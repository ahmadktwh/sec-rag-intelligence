import requests
import json
import logging
from pathlib import Path
from typing import Dict, Optional

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CIKManager:
    """
    Manages the mapping between Stock Tickers and SEC Central Index Keys (CIK).
    Downloads and caches the mapping from SEC.gov for high-performance lookups.
    """
    
    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    CACHE_DIR = Path("data/cache")
    CACHE_FILE = CACHE_DIR / "ticker_to_cik.json"

    def __init__(self, user_agent: str = "SEC-RAG-System admin@example.com"):
        """
        Initialize with a professional User-Agent as required by SEC.
        """
        self.headers = {"User-Agent": user_agent}
        self.ticker_to_cik: Dict[str, str] = {}
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Creates the data/cache directory if it doesn't exist."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def download_mappings(self) -> bool:
        """
        Downloads the latest ticker-to-CIK mapping from SEC.gov.
        """
        try:
            logger.info(f"Downloading master ticker mapping from {self.SEC_TICKERS_URL}")
            response = requests.get(self.SEC_TICKERS_URL, headers=self.headers)
            response.raise_for_status()
            
            # SEC format is { "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ... }
            raw_data = response.json()
            
            processed_data = {}
            for item in raw_data.values():
                ticker = item['ticker'].upper()
                # CIK must be 10 digits padded with leading zeros
                cik = str(item['cik_str']).zfill(10)
                processed_data[ticker] = cik
            
            self.ticker_to_cik = processed_data
            
            # Save to cache
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(self.ticker_to_cik, f, indent=4)
                
            logger.info(f"Successfully cached {len(self.ticker_to_cik)} company mappings.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download SEC mappings: {e}")
            return False

    def load_mappings(self) -> bool:
        """
        Loads mappings from cache, or downloads them if cache is missing.
        """
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    self.ticker_to_cik = json.load(f)
                logger.info(f"Loaded {len(self.ticker_to_cik)} mappings from local cache.")
                return True
            except Exception as e:
                logger.error(f"Error loading cache: {e}. Will attempt re-download.")
        
        return self.download_mappings()

    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Returns the 10-digit CIK for a given ticker.
        """
        ticker = ticker.upper()
        if not self.ticker_to_cik:
            self.load_mappings()
        
        return self.ticker_to_cik.get(ticker)

if __name__ == "__main__":
    # Test the manager
    manager = CIKManager()
    if manager.load_mappings():
        test_ticker = "AAPL"
        cik = manager.get_cik(test_ticker)
        print(f"\n[TEST] Ticker: {test_ticker} -> CIK: {cik}")
        
        test_ticker = "TSLA"
        cik = manager.get_cik(test_ticker)
        print(f"[TEST] Ticker: {test_ticker} -> CIK: {cik}")
