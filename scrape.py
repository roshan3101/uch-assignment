import asyncio
import sys
from pathlib import Path
from typing import List, Optional

import click

sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings
from scraper.browser import BrowserManager, TenderExtractor
from scraper.browser.driver import PageNavigator
from scraper.cleaner import clean_and_deduplicate
from scraper.logger import setup_logging, get_logger
from scraper.metadata import MetadataTracker, generate_run_id, count_tender_types
from scraper.models import Tender, TenderType, TenderStatus
from scraper.search import AdvancedSearch, SearchFilters
from scraper.storage import TenderStorage, MetadataStorage

settings = get_settings()


@click.command()
@click.option(
    '--limit',
    '-l',
    type=int,
    default=None,
    help='Maximum number of tenders to scrape (None = all available)'
)
@click.option(
    '--save-file',
    is_flag=True,
    help='Also save to file in addition to database'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['json']),
    default='json',
    help='File output format if --save-file is used (default: json)'
)
@click.option(
    '--concurrency',
    '-c',
    type=int,
    default=None,
    help='Number of concurrent browser instances (default: from config)'
)
@click.option(
    '--rate-limit',
    '-r',
    type=float,
    default=None,
    help='Delay between requests in seconds (default: from config)'
)
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode (default: headless)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Run without saving data (for testing)'
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    default='INFO',
    help='Logging level (default: INFO)'
)
@click.option(
    '--scrape-details/--no-details',
    default=True,
    help='Scrape full details from detail pages (default: True)'
)
@click.option(
    '--search',
    '-s',
    type=str,
    default=None,
    help='Search keyword to filter tenders'
)
@click.option(
    '--status',
    type=click.Choice(['in_progress', 'closed', 'awarded', 'cancelled']),
    default=None,
    help='Filter by tender status'
)
@click.option(
    '--tender-type',
    type=click.Choice(['goods', 'works', 'services']),
    default=None,
    help='Filter by tender type'
)
@click.option(
    '--organization',
    type=str,
    default=None,
    help='Filter by organization name'
)
@click.option(
    '--min-value',
    type=float,
    default=None,
    help='Minimum estimated value'
)
@click.option(
    '--max-value',
    type=float,
    default=None,
    help='Maximum estimated value'
)
def main(
    limit: Optional[int],
    save_file: bool,
    format: str,
    concurrency: Optional[int],
    rate_limit: Optional[float],
    headless: bool,
    dry_run: bool,
    log_level: str,
    scrape_details: bool,
    search: Optional[str],
    status: Optional[str],
    tender_type: Optional[str],
    organization: Optional[str],
    min_value: Optional[float],
    max_value: Optional[float]
):
    run_id = generate_run_id()
    
    log_file = settings.get_log_path(f"{run_id}.log")
    setup_logging(log_file=log_file, level=log_level, run_id=run_id)
    logger = get_logger(__name__)
    
    logger.info("=" * 70)
    logger.info("TENDER SCRAPER - Starting")
    logger.info("=" * 70)
    logger.info(f"Run ID: {run_id}")
    logger.info(f"Limit: {limit or 'ALL'}")
    logger.info(f"Output Format: {format}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info(f"Scrape Details: {scrape_details}")
    
    if search:
        logger.info(f"Search Keyword: {search}")
    if status:
        logger.info(f"Filter Status: {status}")
    if tender_type:
        logger.info(f"Filter Type: {tender_type}")
    if organization:
        logger.info(f"Filter Organization: {organization}")
    if min_value or max_value:
        logger.info(f"Value Range: {min_value or 0} - {max_value or 'unlimited'}")
    
    if concurrency:
        settings.concurrency = concurrency
    if rate_limit:
        settings.rate_limit = rate_limit
    settings.browser_headless = headless
    
    filters = SearchFilters(
        keyword=search,
        organization=organization,
        tender_type=TenderType[tender_type.upper()] if tender_type else None,
        tender_status=TenderStatus[status.upper()] if status else None,
        min_value=min_value,
        max_value=max_value
    )
    
    config = {
        'limit': limit,
        'format': format,
        'concurrency': settings.concurrency,
        'rate_limit': settings.rate_limit,
        'headless': headless,
        'scrape_details': scrape_details,
        'search_filters': filters.to_dict() if filters.has_filters() else None
    }
    tracker = MetadataTracker(run_id, settings.scraper_version, config)
    
    try:
        tenders = asyncio.run(scrape_tenders(limit, scrape_details, filters, tracker))
        
        logger.info(f"Scraped {len(tenders)} tenders")
        
        logger.info("Cleaning and deduplicating data...")
        original_count = len(tenders)
        tenders = clean_and_deduplicate(tenders)
        tracker.set_deduped_count(original_count - len(tenders))
        tracker.increment_saved(len(tenders))
        
        type_counts = count_tender_types(tenders)
        tracker.update_tender_types(type_counts)
        
        logger.info(f"Final count: {len(tenders)} unique tenders")
        logger.info(f"Tender types: {type_counts}")
        
        if not dry_run:
            logger.info(f"Saving data to {format} file...")
            storage = TenderStorage(settings.output_dir)
            output_path = storage.save(tenders, format=format)
            tracker.set_output_file(str(output_path))
            logger.info(f"[OK] Data saved to: {output_path}")
        else:
            logger.info("Dry run - skipping data save")
        
        metadata = tracker.finalize()
        
        if not dry_run:
            metadata_storage = MetadataStorage(settings.metadata_dir)
            metadata_path = metadata_storage.save_metadata(metadata)
            logger.info(f"[OK] Metadata saved to file: {metadata_path}")
        
        print_summary(metadata, tenders)
        
        logger.info("=" * 70)
        logger.info("SCRAPING COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        tracker.add_error("Interrupted", "User cancelled the operation")
        tracker.finalize()
        return 130
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        tracker.add_error("Fatal", str(e))
        tracker.finalize()
        return 1


async def scrape_tenders(
    limit: Optional[int],
    scrape_details: bool,
    filters: SearchFilters,
    tracker: MetadataTracker
) -> List[Tender]:
    logger = get_logger(__name__)
    
    browser_manager = BrowserManager(settings)
    extractor = TenderExtractor(settings.api_base_url)
    advanced_search = AdvancedSearch(settings.api_base_url)
    
    all_tenders: List[Tender] = []
    
    try:
        await browser_manager.start()
        logger.info("[OK] Browser started")
        
        try:
            context = await browser_manager.create_context()
            page = await context.new_page()
            
            logger.info("Navigating to homepage...")
            navigator = PageNavigator(page, timeout=30000)
            
            if not await navigator.goto(settings.api_base_url):
                raise Exception("Failed to load homepage")
            
            tracker.increment_pages()
            logger.info("[OK] Homepage loaded")
            
            if filters.has_filters():
                logger.info("Applying search filters...")
                if filters.keyword:
                    search_success = await advanced_search.perform_simple_search(page, filters.keyword)
                    if search_success:
                        logger.info(f"[OK] Search completed for: {filters.keyword}")
                    else:
                        logger.warning("Search failed, continuing with homepage results")
                elif filters.tender_status:
                    status_success = await advanced_search.search_by_status(page, filters.tender_status)
                    if status_success:
                        logger.info(f"[OK] Filtered by status: {filters.tender_status.value}")
                else:
                    search_success = await advanced_search.perform_search(page, filters)
                    if search_success:
                        logger.info("[OK] Advanced search completed")
                    else:
                        logger.warning("Advanced search failed, continuing with homepage results")
                
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(2)
            
            logger.info("Extracting tender list...")
            tender_list = await extractor.extract_tender_list(page)
            logger.info(f"[OK] Found {len(tender_list)} tenders")
            
            if limit and len(tender_list) > limit:
                tender_list = tender_list[:limit]
                logger.info(f"Limited to {len(tender_list)} tenders")
        
            if scrape_details:
                logger.info("Scraping full details from detail pages...")
                
                for idx, tender_data in enumerate(tender_list, 1):
                    try:
                        if page.is_closed():
                            logger.error("Main page is closed! Cannot continue.")
                            break
                            
                        tender_id = tender_data['tender_id']
                        # detail_url = f"{settings.api_base_url}/view-nit-home?id={tender_id}" # Not used for clicking
                        
                        logger.info(f"Processing tender {idx}/{len(tender_list)}: {tender_id}")
                        details = await extractor.open_tender_and_extract(
                            page,
                            page.context, 
                            tender_id
                        )
                        
                        if details:
                            tender = Tender(**details)
                            all_tenders.append(tender)
                            tracker.increment_parsed()
                            logger.info(f"[OK] Tender {tender_id} scraped successfully")
                        else:
                            logger.warning(f"Failed to scrape tender {tender_id}")
                            tracker.add_error("DetailScraping", f"Tender {tender_id} failed")
                        
                        if idx < len(tender_list):
                            await asyncio.sleep(settings.rate_limit)
                        
                        if idx % 5 == 0:
                            logger.info(f"Progress: {idx}/{len(tender_list)} tenders with details")
                        
                    except Exception as e:
                        logger.error(f"Error processing tender {idx}: {e}")
                        tracker.add_error("DetailScraping", str(e))
            else:
                logger.info("Processing basic tender information...")
                for idx, tender_data in enumerate(tender_list, 1):
                    try:
                        tender = Tender(
                            tender_id=tender_data['tender_id'],
                            title=tender_data['title'],
                            organization=tender_data['organization'],
                            closing_date=tender_data.get('closing_date'),
                            estimated_value=tender_data.get('estimated_value'),
                            source_url=f"{settings.api_base_url}/view-nit-home?id={tender_data['tender_id']}",
                            ifb_number=tender_data.get('ifb_number'),
                            document_count=tender_data.get('document_count'),
                            raw_html_snippet=tender_data.get('raw_html', '')
                        )
                        
                        all_tenders.append(tender)
                        tracker.increment_parsed()
                        
                        if idx % 10 == 0:
                            logger.info(f"Progress: {idx}/{len(tender_list)} tenders processed")
                        
                    except Exception as e:
                        logger.error(f"Failed to create tender from data: {e}")
                        tracker.add_error("ParseError", str(e))
            
            logger.info(f"[OK] Scraping completed: {len(all_tenders)} tenders")

        finally:
            if 'page' in locals() and page:
                await page.close()
            if 'context' in locals() and context:
                await context.close()
            
    finally:
        await browser_manager.stop()
        logger.info("[OK] Browser stopped")
    
    return all_tenders


async def scrape_detail_pages(
    browser_manager: BrowserManager,
    extractor: TenderExtractor,
    tenders: List[Tender],
    tracker: MetadataTracker
) -> List[Tender]:
    logger = get_logger(__name__)
    detailed_tenders: List[Tender] = []
    
    for idx, tender in enumerate(tenders, 1):
        try:
            logger.info(f"Scraping details for tender {tender.tender_id} ({idx}/{len(tenders)})")
            
            async with browser_manager.managed_page() as page:
                navigator = PageNavigator(page)
                
                detail_url = tender.source_url
                
                if await navigator.goto(detail_url):
                    tracker.increment_pages()
                    
                    detailed_tender = await extractor.extract_tender_details(page, tender.tender_id)
                    
                    if detailed_tender:
                        detailed_tenders.append(detailed_tender)
                    else:
                        detailed_tenders.append(tender)
                        tracker.add_error("DetailExtraction", f"Failed for tender {tender.tender_id}")
                else:
                    logger.warning(f"Failed to load detail page for {tender.tender_id}")
                    detailed_tenders.append(tender)
                    tracker.add_error("Navigation", f"Failed for tender {tender.tender_id}")
            
            await asyncio.sleep(settings.rate_limit)
            
        except Exception as e:
            logger.error(f"Error scraping details for {tender.tender_id}: {e}")
            tracker.add_error("DetailScraping", str(e))
            detailed_tenders.append(tender)
    
    return detailed_tenders


def print_summary(metadata, tenders: List[Tender]):
    print("\n" + "=" * 70)
    print("SCRAPING SUMMARY")
    print("=" * 70)
    print(f"Run ID:              {metadata.run_id}")
    print(f"Duration:            {metadata.duration_seconds:.2f} seconds")
    print(f"Pages Visited:       {metadata.pages_visited}")
    print(f"Tenders Parsed:      {metadata.tenders_parsed}")
    print(f"Tenders Saved:       {metadata.tenders_saved}")
    print(f"Duplicates Removed:  {metadata.deduped_count}")
    print(f"Failures:            {metadata.failures}")
    print()
    print("Tender Types:")
    for tender_type, count in metadata.tender_types_processed.items():
        print(f"  - {tender_type:12} {count:5} tenders")
    print()
    if metadata.output_file:
        print(f"Output File:         {metadata.output_file}")
    print("=" * 70)
    
    if tenders and len(tenders) > 0:
        print("\nSample Tenders (first 3):")
        print("-" * 70)
        for idx, tender in enumerate(tenders[:3], 1):
            print(f"\n{idx}. Tender ID: {tender.tender_id}")
            print(f"   Title: {tender.title[:70]}...")
            print(f"   Organization: {tender.organization}")
            print(f"   Type: {tender.tender_type}")
            print(f"   Closing Date: {tender.closing_date or 'N/A'}")
            print(f"   Value: Rs.{tender.estimated_value:,.2f}" if tender.estimated_value else "   Value: N/A")
        print("-" * 70)


if __name__ == '__main__':
    sys.exit(main())
