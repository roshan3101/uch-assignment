import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config import Settings

logger = logging.getLogger(__name__)


class BrowserManager:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._contexts: list[BrowserContext] = []

    async def start(self):
        logger.info("Starting Playwright browser...")
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.settings.browser_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        
        logger.info(
            f"Browser launched (headless={self.settings.browser_headless})"
        )

    async def stop(self):
        logger.info("Stopping browser...")
        
        for context in self._contexts:
            try:
                await context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
        
        self._contexts.clear()
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.info("Browser stopped")

    async def get_context(self) -> BrowserContext:
        if not self._contexts:
            context = await self.create_context()
            self._contexts.append(context)
        return self._contexts[0]
    
    async def create_context(self) -> BrowserContext:
        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first.")
        
        context = await self.browser.new_context(
            user_agent=self.settings.user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='Asia/Kolkata',  # Indian timezone
            ignore_https_errors=True,  # For gov sites with SSL issues
        )
        
        context.set_default_timeout(self.settings.timeout_seconds * 1000)
        
        self._contexts.append(context)
        logger.debug(f"Created browser context (total: {len(self._contexts)})")
        
        return context

    async def new_page(self, context: Optional[BrowserContext] = None) -> Page:
        if context is None:
            context = await self.create_context()
        
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.debug("Created new page")
        return page

    @asynccontextmanager
    async def managed_page(self):
        context = await self.create_context()
        page = await context.new_page()
        
        try:
            yield page
        finally:
            await page.close()
            await context.close()
            if context in self._contexts:
                self._contexts.remove(context)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


class PageNavigator:

    def __init__(self, page: Page, timeout: int = 30000):
        self.page = page
        self.timeout = timeout

    async def goto(
        self,
        url: str,
        wait_until: str = "networkidle",
        max_retries: int = 3
    ) -> bool:
        for attempt in range(max_retries):
            try:
                logger.debug(f"Navigating to {url} (attempt {attempt + 1})")
                
                response = await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.timeout
                )
                
                if response and response.ok:
                    logger.debug(f"Successfully navigated to {url}")
                    return True
                else:
                    status = response.status if response else "No response"
                    logger.warning(f"Navigation returned status: {status}")
                    
            except Exception as e:
                logger.warning(
                    f"Navigation attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to navigate to {url} after {max_retries} attempts")
                    return False
        
        return False

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None,
        state: str = "visible"
    ) -> bool:
        try:
            await self.page.wait_for_selector(
                selector,
                timeout=timeout or self.timeout,
                state=state
            )
            return True
        except Exception as e:
            logger.warning(f"Element not found: {selector} - {e}")
            return False

    async def wait_for_load_state(self, state: str = "networkidle"):
        try:
            await self.page.wait_for_load_state(state)
        except Exception as e:
            logger.warning(f"Wait for load state failed: {e}")

    async def screenshot(self, path: str, full_page: bool = True):
        try:
            await self.page.screenshot(path=path, full_page=full_page)
            logger.info(f"Screenshot saved to {path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
