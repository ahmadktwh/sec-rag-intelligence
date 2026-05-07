import aiohttp
import asyncio
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional
from .cik_manager import CIKManager

# Setup Logging
logger = logging.getLogger(__name__)

class EdgarFetcher:
    """
    Asynchronous fetcher for SEC EDGAR filings.
    Designed for bulk ingestion with rate-limiting compliance.
    """
    
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"
    
    def __init__(self, user_agent: str = "SEC-RAG-System admin@example.com", rate_limit: int = 10):
        """
        Initialize with User-Agent and rate limit (default 10 req/sec per SEC rules).
        """
        self.headers = {"User-Agent": user_agent}
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.cik_manager = CIKManager(user_agent=user_agent)
        self.raw_data_dir = Path("data/raw_filings")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_json(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Fetches JSON data from a URL with rate limiting."""
        async with self.semaphore:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning(f"Rate limit hit at {url}. Sleeping...")
                        await asyncio.sleep(1) # Backoff
                        return await self.fetch_json(session, url)
                    else:
                        logger.error(f"Failed to fetch {url}: Status {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Request error at {url}: {e}")
                return None

    async def fetch_text(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetches raw text/HTML from a URL with rate limiting."""
        async with self.semaphore:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"Failed to fetch document {url}: Status {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Request error at {url}: {e}")
                return None

    async def get_latest_filings(self, session: aiohttp.ClientSession, ticker: str, filing_type: str = "10-K", count: int = 1) -> List[Dict]:
        """
        Retrieves metadata for the latest filings of a specific type for a ticker.
        """
        cik = self.cik_manager.get_cik(ticker)
        if not cik:
            logger.error(f"CIK not found for ticker {ticker}")
            return []
        
        url = self.SUBMISSIONS_URL.format(cik=cik)
        data = await self.fetch_json(session, url)
        
        if not data:
            return []
        
        recent_filings = data.get('filings', {}).get('recent', {})
        filings = []
        
        for i, f_type in enumerate(recent_filings.get('form', [])):
            if f_type == filing_type:
                accession = recent_filings['accessionNumber'][i].replace('-', '')
                primary_doc = recent_filings['primaryDocument'][i]
                
                filing_meta = {
                    "ticker": ticker,
                    "cik": cik,
                    "accession": accession,
                    "filing_type": filing_type,
                    "report_date": recent_filings['reportDate'][i],
                    "filename": primary_doc,
                    "url": self.ARCHIVES_URL.format(cik=cik.lstrip('0'), accession=accession, filename=primary_doc)
                }
                filings.append(filing_meta)
                if len(filings) >= count:
                    break
        
        return filings

    async def download_filing(self, session: aiohttp.ClientSession, filing_meta: Dict) -> Optional[Path]:
        """
        Downloads the filing document and saves it locally. 
        Implements fallback logic for non-standard SEC URL structures.
        """
        ticker = filing_meta['ticker']
        accession = filing_meta['accession']
        filename = filing_meta['filename']
        cik = filing_meta['cik'].lstrip('0')
        
        save_path = self.raw_data_dir / f"{ticker}_{accession}_{filename}"
        
        if save_path.exists():
            logger.info(f"Filing {ticker} {accession} already exists locally.")
            return save_path
        
        # Strategy 1: Try the direct primary document URL
        content = await self.fetch_text(session, filing_meta['url'])
        
        # Strategy 2: If Strategy 1 fails, browse the directory index.json
        if not content:
            logger.info(f"Direct URL failed for {ticker}. Trying Directory Index fallback...")
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json"
            index_data = await self.fetch_json(session, index_url)
            
            if index_data and 'directory' in index_data and 'item' in index_data['directory']:
                # Look for the primary document or any HTML file that looks like the main filing
                items = index_data['directory']['item']
                found_file = None
                
                # Priority 1: Match exactly the filename we expected
                for item in items:
                    if item['name'] == filename:
                        found_file = item['name']
                        break
                
                # Priority 2: Look for any .htm or .html file if the specific one wasn't found
                if not found_file:
                    for item in items:
                        if item['name'].endswith(('.htm', '.html')) and 'ixbrl' not in item['name'].lower():
                            found_file = item['name']
                            break
                
                if found_file:
                    fallback_url = self.ARCHIVES_URL.format(cik=cik, accession=accession, filename=found_file)
                    content = await self.fetch_text(session, fallback_url)
                    # Update save path to reflect the actual found filename
                    save_path = self.raw_data_dir / f"{ticker}_{accession}_{found_file}"

        if content:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Successfully downloaded filing for {ticker} to {save_path}")
            return save_path
        
        logger.error(f"100% Reliability Check Failed: Could not download filing for {ticker} after fallbacks.")
        return None

async def test_fetcher():
    logging.basicConfig(level=logging.INFO)
    fetcher = EdgarFetcher()
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get latest 10-K for Apple
        logger.info("Testing Apple 10-K fetch...")
        apple_filings = await fetcher.get_latest_filings(session, "AAPL", count=1)
        if apple_filings:
            await fetcher.download_filing(session, apple_filings[0])
            
        # Test 2: Get latest 10-K for Tesla
        logger.info("Testing Tesla 10-K fetch...")
        tesla_filings = await fetcher.get_latest_filings(session, "TSLA", count=1)
        if tesla_filings:
            await fetcher.download_filing(session, tesla_filings[0])

if __name__ == "__main__":
    asyncio.run(test_fetcher())
