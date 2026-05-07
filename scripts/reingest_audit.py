import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from src.ingestion.edgar_fetcher import EdgarFetcher
from src.ingestion.doc_processor import DocumentProcessor
from src.vectorstore.pinecone_store import PineconeStore
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reingest():
    load_dotenv()
    tickers = ["AAPL", "ABBV", "ABT"]
    
    fetcher = EdgarFetcher()
    processor = DocumentProcessor(chunk_size=4000, chunk_overlap=400)
    store = PineconeStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        api_key=os.getenv("PINECONE_API_KEY")
    )
    
    async with aiohttp.ClientSession() as session:
        for ticker in tickers:
            logger.info(f"--- Wiping and Re-ingesting {ticker} ---")
            
            # CRITICAL: Delete old corrupt data first
            store.delete_by_ticker(ticker)
            
            filings = await fetcher.get_latest_filings(session, ticker, count=1)
            if filings:
                file_path = await fetcher.download_filing(session, filings[0])
                if file_path:
                    meta = filings[0]
                    meta['year'] = meta['report_date'].split('-')[0]
                    # Process with 4000 char chunks and layout preservation
                    documents = processor.process_filing(file_path, meta)
                    store.upsert_documents(documents)
                    logger.info(f"✅ Successfully sanitized and re-ingested {ticker}")

if __name__ == "__main__":
    asyncio.run(reingest())
