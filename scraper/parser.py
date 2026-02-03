import re
from typing import Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class HTMLParser:

    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        text = re.sub(r'<[^>]+>', '', text)
        
        text = ' '.join(text.split())

        text = re.sub(r'[^\w\s.,;:()\-/]', '', text)
        
        return text.strip() if text.strip() else None

    @staticmethod
    def extract_text_from_html(html: str, selector: Optional[str] = None) -> str:
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            if selector:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
                return ""
            
            return soup.get_text(strip=True)
            
        except Exception as e:
            logger.warning(f"Failed to parse HTML: {e}")
            return ""

    @staticmethod
    def extract_links(html: str, pattern: Optional[str] = None) -> list[dict]:
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            
            for a_tag in soup.find_all('a', href=True):
                url = a_tag['href']
                text = a_tag.get_text(strip=True)
                
                # Filter by pattern if provided
                if pattern and not re.search(pattern, url):
                    continue
                
                links.append({'text': text, 'url': url})
            
            return links
            
        except Exception as e:
            logger.warning(f"Failed to extract links: {e}")
            return []

    @staticmethod
    def extract_table_data(html: str, table_selector: str = 'table') -> list[list[str]]:
        try:
            soup = BeautifulSoup(html, 'lxml')
            table = soup.select_one(table_selector)
            
            if not table:
                return []
            
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            return rows
            
        except Exception as e:
            logger.warning(f"Failed to extract table data: {e}")
            return []

    @staticmethod
    def remove_html_tags(text: str) -> str:
        return re.sub(r'<[^>]+>', '', text)

    @staticmethod
    def extract_numbers(text: str) -> list[float]:
        pattern = r'[\d,]+\.?\d*'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                num = float(match.replace(',', ''))
                numbers.append(num)
            except ValueError:
                continue
        
        return numbers

    @staticmethod
    def extract_dates(text: str, format_hint: str = 'DD-MM-YYYY') -> list[str]:
        dates = []
        
        patterns = [
            r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match[0]) == 4:  # YYYY-MM-DD format
                        date_str = f"{match[0]}-{match[1]}-{match[2]}"
                    else:  # DD-MM-YYYY or DD/MM/YYYY format
                        date_str = f"{match[2]}-{match[1]}-{match[0]}"
                    
                    dates.append(date_str)
                except:
                    continue
        
        return dates
