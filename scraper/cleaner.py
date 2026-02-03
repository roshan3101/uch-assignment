"""Data cleaning and normalization utilities."""

import logging
import re
from typing import List, Optional
from datetime import datetime

from scraper.models import Tender, TenderType

logger = logging.getLogger(__name__)


class TenderCleaner:

    @staticmethod
    def clean_tender(tender: Tender) -> Tender:

        if tender.title:
            tender.title = TenderCleaner.clean_text(tender.title)
        
        if tender.description:
            tender.description = TenderCleaner.clean_description(tender.description)
        
        if tender.organization:
            tender.organization = TenderCleaner.clean_text(tender.organization)
        
        if tender.publish_date:
            tender.publish_date = TenderCleaner.normalize_date(tender.publish_date)
        
        if tender.closing_date:
            tender.closing_date = TenderCleaner.normalize_date(tender.closing_date)
        
        tender.tender_type = TenderCleaner.validate_tender_type(tender.tender_type)
        
        if tender.location:
            tender.location = TenderCleaner.clean_text(tender.location)
        
        return tender

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        
        text = ' '.join(text.split())
        
        text = re.sub(r'[^\w\s.,;:()\-/&]', '', text)
        
        return text.strip()

    @staticmethod
    def clean_description(description: str) -> str:
        description = TenderCleaner.clean_text(description)
        
        boilerplate_patterns = [
            r'for\s+more\s+details.*',
            r'please\s+visit.*',
            r'click\s+here.*',
            r'download\s+document.*',
        ]
        
        for pattern in boilerplate_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        description = ' '.join(description.split())
        
        if len(description) > 5000:
            description = description[:5000] + "..."
        
        return description.strip()

    @staticmethod
    def normalize_date(date_str: str) -> Optional[str]:
        if not date_str:
            return None
        
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        match = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
        
        match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}"
        
        try:
            dt = datetime.strptime(date_str, '%d-%m-%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
        
        logger.warning(f"Could not normalize date: {date_str}")
        return date_str

    @staticmethod
    def validate_tender_type(tender_type: TenderType) -> TenderType:
        if tender_type in [TenderType.GOODS, TenderType.WORKS, TenderType.SERVICES]:
            return tender_type
        
        return TenderType.UNKNOWN

    @staticmethod
    def deduplicate_tenders(tenders: List[Tender]) -> List[Tender]:
        seen_ids = set()
        unique_tenders = []
        duplicate_count = 0
        
        for tender in tenders:
            if tender.tender_id not in seen_ids:
                seen_ids.add(tender.tender_id)
                unique_tenders.append(tender)
            else:
                duplicate_count += 1
                logger.debug(f"Duplicate tender found: {tender.tender_id}")
        
        if duplicate_count > 0:
            logger.info(f"Removed {duplicate_count} duplicate tenders")
        
        return unique_tenders

    @staticmethod
    def clean_batch(tenders: List[Tender]) -> List[Tender]:
        logger.info(f"Cleaning {len(tenders)} tenders...")
        
        cleaned = []
        failed = 0
        
        for tender in tenders:
            try:
                cleaned_tender = TenderCleaner.clean_tender(tender)
                cleaned.append(cleaned_tender)
            except Exception as e:
                logger.error(f"Failed to clean tender {tender.tender_id}: {e}")
                failed += 1
        
        logger.info(
            f"Cleaned {len(cleaned)} tenders successfully, "
            f"{failed} failed"
        )
        
        return cleaned


def clean_and_deduplicate(tenders: List[Tender]) -> List[Tender]:
    cleaned = TenderCleaner.clean_batch(tenders)
    
    unique = TenderCleaner.deduplicate_tenders(cleaned)
    
    logger.info(
        f"Final count: {len(unique)} unique tenders "
        f"(removed {len(cleaned) - len(unique)} duplicates)"
    )
    
    return unique
