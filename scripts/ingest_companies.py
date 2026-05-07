"""
ingest_companies.py — Bulk Ingestion Script
SEC EDGAR Financial Intelligence RAG System

Usage:
    python scripts/ingest_companies.py

This script:
1. Fetches the latest 10-K filing for each company from SEC EDGAR
2. Sanitizes (wipes) any existing data for that ticker in Pinecone
3. Processes documents into 4000-char, section-tagged chunks
4. Upserts high-quality vectors into the Pinecone index
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
import aiohttp

# Adjust import path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.edgar_fetcher import EdgarFetcher
from src.ingestion.doc_processor import DocumentProcessor
from src.vectorstore.pinecone_store import PineconeStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Top 50 S&P 500 Companies ────────────────────────────────────────────────
COMPANIES = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "CSCO",
    "ADBE", "CRM", "QCOM", "TXN", "AMAT", "IBM", "AMD", "INTC",
    # Consumer / E-Commerce
    "AMZN", "TSLA", "NFLX", "WMT", "COST", "HD", "MCD", "KO",
    "PEP", "DIS", "PG",
    # Financial
    "JPM", "BRK.B", "V", "MA", "BAC", "WFC",
    # Healthcare / Pharma
    "UNH", "JNJ", "ABBV", "ABT", "MRK", "DHR", "TMO", "LLY",
    # Energy / Industrial
    "XOM", "CVX", "CAT", "PM", "LIN", "ACN", "INTU",
]


async def run_ingestion(tickers: list = None):
    """
    Main ingestion loop. Sanitizes + re-ingests each ticker.
    Pass a custom list to ingest only specific companies.
    """
    load_dotenv()

    targets = tickers or COMPANIES
    logger.info(f"Starting ingestion for {len(targets)} companies...")

    fetcher = EdgarFetcher()
    processor = DocumentProcessor(chunk_size=4000, chunk_overlap=400)
    store = PineconeStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        api_key=os.getenv("PINECONE_API_KEY")
    )

    results = {"success": [], "failed": [], "skipped": []}

    async with aiohttp.ClientSession() as session:
        for ticker in targets:
            try:
                logger.info(f"\n{'─'*50}")
                logger.info(f"Processing: {ticker}")

                # Step 1: Wipe stale data
                store.delete_by_ticker(ticker)

                # Step 2: Fetch latest 10-K
                filings = await fetcher.get_latest_filings(session, ticker, count=1)
                if not filings:
                    logger.warning(f"  ⚠ No filings found for {ticker}")
                    results["skipped"].append(ticker)
                    continue

                # Step 3: Download filing
                file_path = await fetcher.download_filing(session, filings[0])
                if not file_path:
                    logger.error(f"  ✗ Download failed for {ticker}")
                    results["failed"].append(ticker)
                    continue

                # Step 4: Process into high-quality chunks
                meta = filings[0]
                meta["year"] = meta["report_date"].split("-")[0]
                documents = processor.process_filing(file_path, meta)

                # Step 5: Upsert to Pinecone
                store.upsert_documents(documents)
                logger.info(f"  ✅ {ticker} — {len(documents)} chunks ingested")
                results["success"].append(ticker)

            except Exception as e:
                logger.error(f"  ✗ Error processing {ticker}: {e}")
                results["failed"].append(ticker)
                continue

    # Final report
    logger.info(f"\n{'═'*50}")
    logger.info(f"INGESTION COMPLETE")
    logger.info(f"  ✅ Success:  {len(results['success'])} tickers")
    logger.info(f"  ⚠ Skipped:  {len(results['skipped'])} tickers")
    logger.info(f"  ✗ Failed:   {len(results['failed'])} tickers")
    if results["failed"]:
        logger.info(f"  Failed tickers: {results['failed']}")
    logger.info(f"{'═'*50}")


if __name__ == "__main__":
    asyncio.run(run_ingestion())
