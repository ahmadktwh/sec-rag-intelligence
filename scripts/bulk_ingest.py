import asyncio
import os
import logging
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

from src.ingestion.edgar_fetcher import EdgarFetcher
from src.ingestion.doc_processor import DocumentProcessor
from src.vectorstore.pinecone_store import PineconeStore

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def ingest_company(session, ticker, fetcher, processor, store):
    """Pipeline for a single company with error handling."""
    try:
        logger.info(f"--- Processing {ticker} ---")
        
        # 1. Fetch
        filings = await fetcher.get_latest_filings(session, ticker, filing_type="10-K", count=1)
        if not filings:
            logger.warning(f"No filings found for {ticker}")
            return False
        
        filing_meta = filings[0]
        file_path = await fetcher.download_filing(session, filing_meta)
        
        if not file_path:
            return False
        
        # 2. Process
        filing_meta['year'] = filing_meta['report_date'].split('-')[0]
        documents = processor.process_filing(file_path, filing_meta)
        
        if not documents:
            return False
        
        # 3. Store
        store.upsert_documents(documents)
        logger.info(f"✅ Successfully ingested {ticker}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error for {ticker}: {e}")
        return False

async def main(tickers: list, batch_size: int = 5):
    """
    Orchestrates bulk ingestion in SMALL BATCHES.
    This prevents SEC rate limits and local crashes.
    """
    load_dotenv()
    
    fetcher = EdgarFetcher()
    processor = DocumentProcessor()
    store = PineconeStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        api_key=os.getenv("PINECONE_API_KEY")
    )
    
    async with aiohttp.ClientSession() as session:
        # Process in batches
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            logger.info(f"\n🚀 Starting Batch: {batch}")
            
            tasks = [ingest_company(session, ticker, fetcher, processor, store) for ticker in batch]
            results = await asyncio.gather(*tasks)
            
            success_count = sum(1 for r in results if r)
            logger.info(f"📊 Batch Finished: {success_count}/{len(batch)} successful.")
            
            # Wait 2 seconds between batches to be extra safe with SEC
            if i + batch_size < len(tickers):
                logger.info("Sleeping for 2s to respect rate limits...")
                await asyncio.sleep(2)

if __name__ == "__main__":
    # Only the 21 Missing Tickers
    target_tickers = [
        "MSFT", "JPM", "PG", "HD", "MRK", "COST", "CVX", "CRM", "BAC", "TMO", 
        "ABT", "AMD", "ORCL", "WMT", "DHR", "PFE", "PM", "COP", "QCOM", "UPS", "IBM"
    ]
    
    logger.info(f"Starting Robust Batch Ingestion for {len(target_tickers)} companies...")
    asyncio.run(main(target_tickers, batch_size=5))
