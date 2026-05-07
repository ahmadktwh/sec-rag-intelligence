import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

from src.ingestion.edgar_fetcher import EdgarFetcher
from src.ingestion.doc_processor import DocumentProcessor
from src.vectorstore.pinecone_store import PineconeStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Top 50 S&P 500 Tickers for a professional Financial RAG
TOP_50_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK.B", "TSLA", "AVGO", "LLY",
    "JPM", "UNH", "V", "MA", "XOM", "HD", "PG", "COST", "JNJ", "ORCL",
    "ABBV", "BAC", "HD", "CVX", "MRK", "NFLX", "AMD", "ADBE", "CRM", "PEP",
    "WMT", "KO", "TMO", "CSCO", "ABT", "ACN", "DIS", "MCD", "LIN", "PM",
    "INTC", "TXN", "VZ", "WFC", "DHR", "INTU", "QCOM", "CAT", "AMAT", "IBM"
]

async def bulk_sanitize_and_ingest():
    load_dotenv()
    
    fetcher = EdgarFetcher()
    processor = DocumentProcessor(chunk_size=4000, chunk_overlap=400)
    store = PineconeStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        api_key=os.getenv("PINECONE_API_KEY")
    )
    
    async with aiohttp.ClientSession() as session:
        for ticker in TOP_50_TICKERS:
            try:
                logger.info(f"\n--- Processing {ticker} (Sanitized Mode) ---")
                
                # 1. Wipe existing data for this ticker (removes old corrupt 512-char chunks)
                store.delete_by_ticker(ticker)
                
                # 2. Fetch latest 10-K
                filings = await fetcher.get_latest_filings(session, ticker, count=1)
                if not filings:
                    logger.warning(f"No filings found for {ticker}")
                    continue
                    
                file_path = await fetcher.download_filing(session, filings[0])
                if file_path:
                    meta = filings[0]
                    meta['year'] = meta['report_date'].split('-')[0]
                    
                    # 3. Process with high-quality settings
                    documents = processor.process_filing(file_path, meta)
                    
                    # 4. Ingest new clean data
                    store.upsert_documents(documents)
                    logger.info(f"✅ {ticker} is now sanitized and high-quality.")
                else:
                    logger.error(f"Failed to download filing for {ticker}")
                    
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                continue

if __name__ == "__main__":
    asyncio.run(bulk_sanitize_and_ingest())
