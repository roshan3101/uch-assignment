import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from playwright.async_api import Page

from scraper.models import Tender, TenderType, TenderStatus, Attachment

logger = logging.getLogger(__name__)


class TenderExtractor:

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def extract_tender_list(self, page: Page) -> List[Dict[str, Any]]:
        logger.info("Extracting tender list from page...")
        
        tenders = []
        
        try:
            await page.wait_for_selector('table', timeout=10000)
            
            rows = await page.query_selector_all('tbody tr')
            logger.info(f"Found {len(rows)} tender rows")
            
            for idx, row in enumerate(rows):
                try:
                    tender_data = await self._extract_row_data(row)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Failed to extract row {idx}: {e}")
            
            logger.info(f"Successfully extracted {len(tenders)} tenders")
            
        except Exception as e:
            logger.error(f"Failed to extract tender list: {e}")
        
        return tenders

    async def _extract_row_data(self, row) -> Optional[Dict[str, Any]]:
        try:
            cells = await row.query_selector_all('td')
            
            if len(cells) < 3:
                return None
            
            # Column 1: IFB Number
            ifb_number = await cells[0].inner_text()
            
            # Column 2: Tender details (HTML with links)
            details_html = await cells[1].inner_html()
            
            # Column 3: Document info
            doc_html = await cells[2].inner_html()
            
            # Extract tender ID from details
            tender_id = self._extract_tender_id_from_html(details_html)
            if not tender_id:
                return None
            
            # Extract other fields
            organization = self._extract_organization(details_html)
            title = self._extract_title(details_html)
            estimated_value = self._extract_estimated_value(details_html)
            closing_date = self._extract_closing_date(details_html)
            document_count = self._extract_document_count(doc_html)
            
            return {
                'tender_id': tender_id,
                'ifb_number': ifb_number.strip(),
                'organization': organization,
                'title': title,
                'estimated_value': estimated_value,
                'closing_date': closing_date,
                'document_count': document_count,
                'raw_html': details_html[:500]
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract row data: {e}")
            return None

    async def extract_tender_details(self, page: Page, tender_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Extracting details for tender {tender_id}")
        
        try:
            # Wait for content to load
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Extract all text content
            content = await page.content()
            
            # Extract fields
            title = await self._extract_detail_field(page, 'title')
            organization = await self._extract_detail_field(page, 'organization')
            description = await self._extract_description(page)
            publish_date = await self._extract_date_field(page, 'publish')
            closing_date = await self._extract_date_field(page, 'closing')
            estimated_value = await self._extract_value_field(page)
            location = await self._extract_detail_field(page, 'location')
            category = await self._extract_detail_field(page, 'category')
            department = await self._extract_detail_field(page, 'department')
            ifb_number = await self._extract_ifb_number(page)
            
            # Extract additional details
            eligibility = await self._extract_eligibility(page)
            specifications = await self._extract_specifications(page)
            terms_conditions = await self._extract_terms(page)
            terms_conditions = await self._extract_terms(page)
            contact_info = await self._extract_contact_info(page)
            tender_fee = await self._extract_tender_fee(page)
            emd_amount = await self._extract_emd_amount(page)
            
            # Refine estimated value from script if possible
            script_value = await self._extract_script_value(page, 'ecvvalue')
            if script_value is not None:
                estimated_value = script_value
            
            # Determine tender type and status
            tender_type = self._determine_tender_type(title, organization, description)
            tender_status = await self._extract_status(page)
            
            # Build source URL
            source_url = page.url
            
            details = {
                'tender_id': tender_id,
                'title': title or f"Tender {tender_id}",
                'organization': organization or "Unknown Organization",
                'tender_type': tender_type,
                'tender_status': tender_status,
                'publish_date': publish_date,
                'closing_date': closing_date,
                'estimated_value': estimated_value,
                'description': description,
                'source_url': source_url,
                'ifb_number': ifb_number,
                'location': location,
                'department': department,
                'category': category,
                'eligibility': eligibility,
                'specifications': specifications,
                'terms_conditions': terms_conditions,
                'specifications': specifications,
                'terms_conditions': terms_conditions,
                'contact_info': contact_info,
                'tender_fee': tender_fee,
                'emd_amount': emd_amount,
                'raw_html_snippet': content[:1000]
            }
            
            logger.info(f"✓ Successfully extracted details for tender {tender_id}")
            return details
            
        except Exception as e:
            logger.error(f"Failed to extract tender details for {tender_id}: {e}")
            return None
    
    async def open_tender_and_extract(self, page: Page, context, tender_id: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Clicking link for tender {tender_id}...")
        
        new_page = None
        try:
            link_selector = f'a:has-text("Tender Id :{tender_id}")'
            
            async with context.expect_page() as page_info:
               await page.click(link_selector)
            
            new_page = await page_info.value
            await new_page.wait_for_load_state('networkidle', timeout=30000)
            
            # Log page info for debugging
            try:
                page_title = await new_page.title()
                logger.info(f"New page loaded: {page_title}")
            except Exception as log_err:
                logger.warning(f"Failed to log page info: {log_err}")

            details = await self.extract_tender_details(new_page, tender_id)
            
            if details:
                doc_url = await self._find_document_link(new_page)
                if doc_url:
                    attachments = await self.extract_documents_in_new_tab(context, doc_url)
                    details['attachments'] = attachments
                    details['document_count'] = len(attachments)
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to open/extract tender {tender_id}: {e}")
            return None
        finally:
            if new_page:
                try:
                    await new_page.close()
                except:
                    pass
    
    async def extract_documents_in_new_tab(self, context, doc_url: str) -> List[Attachment]:
        logger.info(f"Opening documents in new tab: {doc_url}")
        
        new_page = None
        try:
            new_page = await context.new_page()
            await new_page.goto(doc_url, wait_until='networkidle', timeout=30000)
            
            attachments = await self.extract_documents(new_page)
            
            return attachments
            
        except Exception as e:
            logger.error(f"Failed to extract documents in new tab: {e}")
            return []
        finally:
            if new_page:
                await new_page.close()
    
    async def _find_document_link(self, page: Page) -> Optional[str]:
        selectors = [
            'a:has-text("Documents")',
            'a:has-text("Attachments")',
            'a:has-text("Download")',
            'a[href*="document"]',
            'a[href*="attachment"]'
        ]
        
        for selector in selectors:
            try:
                link = await page.query_selector(selector)
                if link:
                    href = await link.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            return f"{self.base_url}{href}"
                        return href
            except:
                continue
        
        return None

    async def extract_documents(self, page: Page) -> List[Attachment]:
        logger.info("Extracting documents...")
        
        attachments = []
        
        try:
            # Wait for document list
            await page.wait_for_selector('table, .document-list', timeout=10000)
            
            # Find all document links
            links = await page.query_selector_all('a[href*="download"], a[href*=".pdf"]')
            
            for link in links:
                try:
                    name = await link.inner_text()
                    href = await link.get_attribute('href')
                    
                    if href:
                        # Make absolute URL
                        if not href.startswith('http'):
                            url = f"{self.base_url}{href}"
                        else:
                            url = href
                        
                        # Determine file type
                        file_type = self._get_file_extension(url)
                        
                        attachment = Attachment(
                            name=name.strip() or f"Document_{len(attachments) + 1}",
                            url=url,
                            type=file_type
                        )
                        
                        attachments.append(attachment)
                        
                except Exception as e:
                    logger.warning(f"Failed to extract document link: {e}")
            
            logger.info(f"Extracted {len(attachments)} documents")
            
        except Exception as e:
            logger.warning(f"Failed to extract documents: {e}")
        
        return attachments

    
    def _extract_tender_id_from_html(self, html: str) -> Optional[str]:
        match = re.search(r'Tender[_ ]?Id[:\s]+(\d+)', html, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_organization(self, html: str) -> str:
        match = re.search(r'<span[^>]*style="[^"]*color:#f44336[^"]*"[^>]*>([^<]+)', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        match = re.search(r'>([^<]+)<form', html, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if len(text) > 3 and "tender" not in text.lower():
                return text
                
        return "Unknown Organization"

    def _extract_title(self, html: str) -> str:
        match = re.search(r'Name Of Work\s*:<\/strong>([^<]+)', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Untitled Tender"

    def _extract_estimated_value(self, html: str) -> Optional[float]:
        match = re.search(r'Estimated Contract Value\s*:\s*([\d,]+\.?\d*)', html, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None

    def _extract_closing_date(self, html: str) -> Optional[str]:
        match = re.search(r'Last Date.*?Submission\s*:\s*(\d{2}-\d{2}-\d{4})', html, re.IGNORECASE)
        if match:
            try:
                day, month, year = match.group(1).split('-')
                return f"{year}-{month}-{day}"
            except ValueError:
                return None
        return None

    def _extract_document_count(self, html: str) -> Optional[int]:
        match = re.search(r'Total No:(\d+)', html)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    async def _extract_detail_field(self, page: Page, field: str) -> Optional[str]:
        selectors = {
            'title': ['h1', 'h2', '.tender-title', '[class*="title"]'],
            'organization': ['.organization', '[class*="org"]', 'td:has-text("Organization")'],
            'location': ['[class*="location"]', 'td:has-text("Location")'],
            'category': ['[class*="category"]', 'td:has-text("Category")'],
        }
        
        for selector in selectors.get(field, []):
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    return text.strip() if text else None
            except:
                continue
        
        return None

    async def _extract_description(self, page: Page) -> Optional[str]:
        selectors = ['.description', '[class*="desc"]', 'div.content', 'p']
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = []
                    for elem in elements[:5]:  # First 5 paragraphs
                        text = await elem.inner_text()
                        if text and len(text) > 20:
                            texts.append(text.strip())
                    
                    if texts:
                        return ' '.join(texts)
            except:
                continue
        
        return None

    async def _extract_date_field(self, page: Page, date_type: str) -> Optional[str]:
        keywords = {
            'publish': ['publish', 'posted', 'released'],
            'closing': ['closing', 'deadline', 'last date', 'submission']
        }
        
        content = await page.content()
        
        for keyword in keywords.get(date_type, []):
            pattern = f'{keyword}.*?(\\d{{2}}-\\d{{2}}-\\d{{4}})'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    day, month, year = match.group(1).split('-')
                    return f"{year}-{month}-{day}"
                except:
                    continue
        
        return None

    async def _extract_value_field(self, page: Page) -> Optional[float]:
        content = await page.content()
        
        patterns = [
            r'Estimated.*?Value.*?([\d,]+\.?\d*)',
            r'Contract.*?Value.*?([\d,]+\.?\d*)',
            r'Amount.*?([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except:
                    continue
        
        return None

    def _determine_tender_type(
        self,
        title: Optional[str],
        organization: Optional[str],
        description: Optional[str]
    ) -> TenderType:
        text = ' '.join(filter(None, [title, organization, description])).lower()
        
        works_keywords = ['construction', 'building', 'road', 'bridge', 'repair', 'maintenance']
        goods_keywords = ['supply', 'purchase', 'procurement', 'equipment', 'goods']
        services_keywords = ['consultancy', 'service', 'management', 'operation', 'audit']
        
        works_count = sum(1 for kw in works_keywords if kw in text)
        goods_count = sum(1 for kw in goods_keywords if kw in text)
        services_count = sum(1 for kw in services_keywords if kw in text)
        
        max_count = max(works_count, goods_count, services_count)
        
        if max_count == 0:
            return TenderType.UNKNOWN
        elif works_count == max_count:
            return TenderType.WORKS
        elif goods_count == max_count:
            return TenderType.GOODS
        else:
            return TenderType.SERVICES

    def _get_file_extension(self, url: str) -> str:
        match = re.search(r'\.([a-zA-Z0-9]+)(?:\?|$)', url)
        return match.group(1).lower() if match else 'unknown'
    
    async def _extract_ifb_number(self, page: Page) -> Optional[str]:
        content = await page.content()
        patterns = [
            r'IFB[_ ]?No\.?\s*:?\s*([A-Z0-9\-/]+)',
            r'Tender[_ ]?No\.?\s*:?\s*([A-Z0-9\-/]+)',
            r'Notice[_ ]?No\.?\s*:?\s*([A-Z0-9\-/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def _extract_status(self, page: Page) -> TenderStatus:
        """Extract tender status from page."""
        content = (await page.content()).lower()
        
        if any(word in content for word in ['awarded', 'winner', 'awardee']):
            return TenderStatus.AWARDED
        elif any(word in content for word in ['closed', 'expired', 'deadline passed']):
            return TenderStatus.CLOSED
        elif any(word in content for word in ['cancelled', 'canceled', 'withdrawn']):
            return TenderStatus.CANCELLED
        elif any(word in content for word in ['in progress', 'active', 'open']):
            return TenderStatus.IN_PROGRESS
        
        return TenderStatus.UNKNOWN
    
    async def _extract_eligibility(self, page: Page) -> Optional[str]:
        """Extract eligibility criteria."""
        selectors = [
            '[class*="eligibility"]',
            'div:has-text("Eligibility")',
            'h3:has-text("Eligibility") + *',
            'section:has-text("Criteria")'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 20:
                        return text.strip()
            except:
                continue
        
        return None
    
    async def _extract_specifications(self, page: Page) -> Optional[str]:
        """Extract technical specifications."""
        selectors = [
            '[class*="specification"]',
            '[class*="technical"]',
            'div:has-text("Specification")',
            'div:has-text("Technical")',
            'h3:has-text("Specifications") + *'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 20:
                        return text.strip()[:500]  # Limit length
            except:
                continue
        
        return None
    
    async def _extract_terms(self, page: Page) -> Optional[str]:
        """Extract terms and conditions."""
        selectors = [
            '[class*="terms"]',
            '[class*="conditions"]',
            'div:has-text("Terms and Conditions")',
            'div:has-text("Terms & Conditions")',
            'h3:has-text("Terms") + *'
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 20:
                        return text.strip()[:500]  # Limit length
            except:
                continue
        
        return None
    
    async def _extract_contact_info(self, page: Page) -> Optional[Dict[str, str]]:
        """Extract contact information."""
        content = await page.content()
        
        contact_info = {}
        
        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
        if email_match:
            contact_info['email'] = email_match.group(0)
        
        # Phone
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{10}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, content)
            if phone_match:
                contact_info['phone'] = phone_match.group(0)
                break
        
        # Address (look for common address patterns)
        address_selectors = [
            '[class*="address"]',
            '[class*="contact"]',
            'div:has-text("Address")',
            'p:has-text("Address")'
        ]
        
        for selector in address_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 10 and len(text) < 200:
                        contact_info['address'] = text.strip()
                        break
            except:
                continue
        
        return contact_info if contact_info else None

    async def _extract_script_value(self, page: Page, var_name: str) -> Optional[float]:
        content = await page.content()
        match = re.search(f'var {var_name}\s*=\s*([\d\.]+)', content)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return None

    async def _extract_tender_fee(self, page: Page) -> Optional[float]:
        return await self._extract_script_value(page, 'tenderfee')

    async def _extract_emd_amount(self, page: Page) -> Optional[str]:
        content = await page.content()
        # Look for var emdfee='...';
        match = re.search(r"var emdfee\s*=\s*'([^']+)'", content)
        if match:
            return match.group(1)
        return None
