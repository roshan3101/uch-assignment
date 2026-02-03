"""Advanced search functionality for tender scraping."""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from playwright.async_api import Page

from scraper.models import TenderType, TenderStatus

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    keyword: Optional[str] = None
    tender_id: Optional[str] = None
    organization: Optional[str] = None
    
    # Type and status
    tender_type: Optional[TenderType] = None
    tender_status: Optional[TenderStatus] = None
    
    # Date ranges
    publish_date_from: Optional[date] = None
    publish_date_to: Optional[date] = None
    closing_date_from: Optional[date] = None
    closing_date_to: Optional[date] = None
    
    # Value ranges
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    # Location and category
    location: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    
    # Pagination
    page_number: int = 1
    page_size: int = 50
    
    def to_dict(self) -> Dict:
        filters = {}
        
        if self.keyword:
            filters['keyword'] = self.keyword
        if self.tender_id:
            filters['tenderId'] = self.tender_id
        if self.organization:
            filters['organization'] = self.organization
        if self.tender_type:
            filters['tenderType'] = self.tender_type.value
        if self.tender_status:
            filters['tenderStatus'] = self.tender_status.value
        if self.publish_date_from:
            filters['publishDateFrom'] = self.publish_date_from.strftime('%d-%m-%Y')
        if self.publish_date_to:
            filters['publishDateTo'] = self.publish_date_to.strftime('%d-%m-%Y')
        if self.closing_date_from:
            filters['closingDateFrom'] = self.closing_date_from.strftime('%d-%m-%Y')
        if self.closing_date_to:
            filters['closingDateTo'] = self.closing_date_to.strftime('%d-%m-%Y')
        if self.min_value is not None:
            filters['minValue'] = str(self.min_value)
        if self.max_value is not None:
            filters['maxValue'] = str(self.max_value)
        if self.location:
            filters['location'] = self.location
        if self.category:
            filters['category'] = self.category
        if self.department:
            filters['department'] = self.department
        
        filters['pageNumber'] = str(self.page_number)
        filters['pageSize'] = str(self.page_size)
        
        return filters
    
    def has_filters(self) -> bool:
        return any([
            self.keyword, self.tender_id, self.organization,
            self.tender_type, self.tender_status,
            self.publish_date_from, self.publish_date_to,
            self.closing_date_from, self.closing_date_to,
            self.min_value, self.max_value,
            self.location, self.category, self.department
        ])


class AdvancedSearch:
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def perform_search(
        self,
        page: Page,
        filters: SearchFilters
    ) -> bool:
        logger.info(f"Performing advanced search with filters: {filters.to_dict()}")
        
        try:
            if '/advanced-search' not in page.url:
                await page.goto(f"{self.base_url}/advanced-search", wait_until='networkidle')
            
            await page.wait_for_selector('form, #searchForm', timeout=10000)
            
            await self._fill_search_form(page, filters)
            
            await self._submit_search(page)
            
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            logger.info("✓ Advanced search completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return False
    
    async def perform_simple_search(
        self,
        page: Page,
        keyword: str
    ) -> bool:
        logger.info(f"Performing simple search: '{keyword}'")
        
        try:
            search_selectors = [
                'input[name="search"]',
                'input[type="search"]',
                'input[placeholder*="Search"]',
                '#searchBox',
                '.search-input'
            ]
            
            for selector in search_selectors:
                try:
                    search_box = await page.query_selector(selector)
                    if search_box:
                        await search_box.fill('')
                        await search_box.type(keyword, delay=100)
                        
                        await search_box.press('Enter')
                        
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        
                        logger.info(f"✓ Simple search for '{keyword}' completed")
                        return True
                        
                except:
                    continue
            
            filters = SearchFilters(keyword=keyword)
            return await self.perform_search(page, filters)
            
        except Exception as e:
            logger.error(f"Simple search failed: {e}")
            return False
    
    async def search_by_status(
        self,
        page: Page,
        status: TenderStatus
    ) -> bool:
        logger.info(f"Searching for {status.value} tenders")
        
        try:
            status_selectors = [
                f'button:has-text("{status.value}")',
                f'a:has-text("{status.value}")',
                f'[data-status="{status.value}"]',
                f'.status-{status.value.lower().replace(" ", "-")}'
            ]
            
            for selector in status_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        logger.info(f"✓ Filtered by status: {status.value}")
                        return True
                except:
                    continue
            
            filters = SearchFilters(tender_status=status)
            return await self.perform_search(page, filters)
            
        except Exception as e:
            logger.error(f"Status search failed: {e}")
            return False
    
    async def _fill_search_form(self, page: Page, filters: SearchFilters) -> None:
        if filters.keyword:
            await self._fill_field(page, ['#keyword', 'input[name*="keyword"]'], filters.keyword)
        
        if filters.tender_id:
            await self._fill_field(page, ['#tenderId', 'input[name*="tender"]'], filters.tender_id)
        
        if filters.organization:
            await self._fill_field(page, ['#organization', 'input[name*="org"]'], filters.organization)
        
        if filters.tender_type:
            await self._select_dropdown(
                page,
                ['#tenderType', 'select[name*="type"]'],
                filters.tender_type.value
            )
        
        if filters.tender_status:
            await self._select_dropdown(
                page,
                ['#tenderStatus', 'select[name*="status"]'],
                filters.tender_status.value
            )
        
        if filters.publish_date_from:
            await self._fill_date_field(
                page,
                ['#publishDateFrom', 'input[name*="publish"][name*="from"]'],
                filters.publish_date_from
            )
        
        if filters.publish_date_to:
            await self._fill_date_field(
                page,
                ['#publishDateTo', 'input[name*="publish"][name*="to"]'],
                filters.publish_date_to
            )
        
        if filters.closing_date_from:
            await self._fill_date_field(
                page,
                ['#closingDateFrom', 'input[name*="closing"][name*="from"]'],
                filters.closing_date_from
            )
        
        if filters.closing_date_to:
            await self._fill_date_field(
                page,
                ['#closingDateTo', 'input[name*="closing"][name*="to"]'],
                filters.closing_date_to
            )
        
        if filters.min_value is not None:
            await self._fill_field(
                page,
                ['#minValue', 'input[name*="min"][name*="value"]'],
                str(filters.min_value)
            )
        
        if filters.max_value is not None:
            await self._fill_field(
                page,
                ['#maxValue', 'input[name*="max"][name*="value"]'],
                str(filters.max_value)
            )
        
        if filters.location:
            await self._fill_field(page, ['#location', 'input[name*="location"]'], filters.location)
        
        if filters.category:
            await self._fill_field(page, ['#category', 'select[name*="category"]'], filters.category)
        
        if filters.department:
            await self._fill_field(page, ['#department', 'input[name*="department"]'], filters.department)
    
    async def _fill_field(self, page: Page, selectors: List[str], value: str) -> bool:
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.fill(value)
                    return True
            except:
                continue
        return False
    
    async def _select_dropdown(self, page: Page, selectors: List[str], value: str) -> bool:
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.select_option(value)
                    return True
            except:
                continue
        return False
    
    async def _fill_date_field(self, page: Page, selectors: List[str], date_value: date) -> bool:
        date_str = date_value.strftime('%d-%m-%Y')
        return await self._fill_field(page, selectors, date_str)
    
    async def _submit_search(self, page: Page) -> None:
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button:has-text("Find")',
            '#searchButton',
            '.search-button'
        ]
        
        for selector in submit_selectors:
            try:
                button = await page.query_selector(selector)
                if button:
                    await button.click()
                    return
            except:
                continue
        
        try:
            first_input = await page.query_selector('input[type="text"]')
            if first_input:
                await first_input.press('Enter')
        except:
            pass
