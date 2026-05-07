"""
============================================================
 PINECONE DATABASE AUDIT & CORRUPTION CHECKER
 Audits every ticker's data quality in the Pinecone index.
============================================================
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
logging.basicConfig(level=logging.WARNING)  # Suppress noise

TICKERS = ["AAPL", "ABBV", "ABT"]
PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
api_key    = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")
google_key = os.getenv("GOOGLE_API_KEY")

if not api_key or not index_name or not google_key:
    print(f"{FAIL} Missing environment variables. Check .env file.")
    sys.exit(1)

print("\n" + "="*60)
print(" PINECONE DATABASE AUDIT REPORT")
print("="*60)

# ─────────────────────────────────────────────
# TEST 1: CONNECTION TEST
# ─────────────────────────────────────────────
print("\n[TEST 1] CONNECTION & INDEX VERIFICATION")
print("-"*40)
try:
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    namespaces    = stats.get("namespaces", {})
    print(f"{PASS} Connected to Pinecone successfully.")
    print(f"       Index Name : {index_name}")
    print(f"       Total Vectors : {total_vectors}")
    print(f"       Namespaces : {list(namespaces.keys()) or ['default (empty string)']}")
    if total_vectors == 0:
        print(f"{FAIL} INDEX IS EMPTY! No data found. Re-ingestion needed.")
        sys.exit(1)
except Exception as e:
    print(f"{FAIL} Connection failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────
# TEST 2: EMBEDDING MODEL
# ─────────────────────────────────────────────
print("\n[TEST 2] EMBEDDING MODEL HEALTH CHECK")
print("-"*40)
try:
    embedder = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=google_key,
        task_type="retrieval_query"
    )
    test_vec = embedder.embed_query("What is the total revenue?")
    dim = len(test_vec)
    if dim > 0:
        print(f"{PASS} Embedding model is working. Vector dimension: {dim}")
    else:
        print(f"{FAIL} Embedding model returned empty vector.")
except Exception as e:
    print(f"{FAIL} Embedding model error: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────
# TEST 3: PER-TICKER DATA AUDIT
# ─────────────────────────────────────────────
print("\n[TEST 3] PER-TICKER DATA QUALITY AUDIT")
print("-"*40)

audit_results = {}
CORRUPTION_INDICATORS = [
    "xbrl", "xmlns", "contextref", "unitref",   # Raw XML/XBRL tags
    "&#x", "&amp;", "&lt;", "&gt;",             # HTML entities
]

for ticker in TICKERS:
    print(f"\n  [{ticker}] Auditing...")
    result = {"chunks": 0, "avg_len": 0, "has_metadata": True,
              "corrupt_chunks": 0, "sections_found": set(), "sample_text": ""}

    try:
        # Search with a generic financial query
        query_vec = embedder.embed_query(f"{ticker} annual revenue income financial statements")
        response = index.query(
            vector=query_vec,
            top_k=15,
            include_metadata=True,
            filter={"ticker": {"$eq": ticker}}
        )
        matches = response.get("matches", [])
        result["chunks"] = len(matches)

        if len(matches) == 0:
            print(f"  {FAIL} [{ticker}] NO DATA FOUND IN INDEX! This ticker was not ingested.")
            audit_results[ticker] = result
            continue

        total_len = 0
        corrupt_count = 0
        sections = set()

        for match in matches:
            meta = match.get("metadata", {})
            text = meta.get("text", "")
            section = meta.get("section", "Unknown")
            sections.add(section)
            total_len += len(text)

            # Check for corruption signals
            is_corrupt = False
            if len(text) < 100:
                is_corrupt = True  # Too short = fragmented/corrupt chunk
            for indicator in CORRUPTION_INDICATORS:
                if indicator.lower() in text.lower():
                    is_corrupt = True
                    break
            if is_corrupt:
                corrupt_count += 1

        result["avg_len"]        = total_len // len(matches)
        result["corrupt_chunks"] = corrupt_count
        result["sections_found"] = sections
        result["sample_text"]    = matches[0]["metadata"].get("text", "")[:300]

        # Per-ticker verdict
        c_rate = (corrupt_count / len(matches)) * 100
        if corrupt_count == 0:
            print(f"  {PASS} [{ticker}] {len(matches)} chunks | Avg length: {result['avg_len']} chars | Sections: {sections}")
        elif c_rate < 30:
            print(f"  {WARN} [{ticker}] {len(matches)} chunks | {corrupt_count} suspect chunks ({c_rate:.0f}%) | Sections: {sections}")
        else:
            print(f"  {FAIL} [{ticker}] HIGH CORRUPTION: {corrupt_count}/{len(matches)} chunks ({c_rate:.0f}%) are corrupt!")

    except Exception as e:
        print(f"  {FAIL} [{ticker}] Query failed: {e}")

    audit_results[ticker] = result

# ─────────────────────────────────────────────
# TEST 4: FINANCIAL DATA RETRIEVAL TEST
# ─────────────────────────────────────────────
print("\n[TEST 4] FINANCIAL DATA RETRIEVAL QUALITY TEST")
print("-"*40)

FINANCIAL_QUERIES = [
    "total revenue net sales",
    "net income operating income",
    "earnings per share EPS",
]

for ticker in TICKERS:
    print(f"\n  [{ticker}] Financial Search Quality:")
    best_hit = None
    best_score = 0

    for q in FINANCIAL_QUERIES:
        qvec = embedder.embed_query(f"{ticker} {q}")
        resp = index.query(
            vector=qvec,
            top_k=3,
            include_metadata=True,
            filter={"ticker": {"$eq": ticker}}
        )
        for match in resp.get("matches", []):
            if match["score"] > best_score:
                best_score = match["score"]
                best_hit = match["metadata"].get("text", "")[:400]

    if best_score > 0.75:
        print(f"  {PASS} Best similarity score: {best_score:.4f} (High confidence)")
    elif best_score > 0.60:
        print(f"  {WARN} Best similarity score: {best_score:.4f} (Medium confidence — may miss some data)")
    else:
        print(f"  {FAIL} Best similarity score: {best_score:.4f} (LOW — financial data likely missing!)")

    if best_hit:
        print(f"         Sample retrieved text snippet:")
        print(f"         >>> {best_hit[:200].strip()}...")

# ─────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────
print("\n" + "="*60)
print(" AUDIT SUMMARY")
print("="*60)
all_ok = True
for ticker in TICKERS:
    r = audit_results.get(ticker, {})
    chunks  = r.get("chunks", 0)
    corrupt = r.get("corrupt_chunks", 0)
    avg_len = r.get("avg_len", 0)
    sections = r.get("sections_found", set())

    if chunks == 0:
        status = FAIL
        all_ok = False
        verdict = "NO DATA — Must re-ingest!"
    elif corrupt / max(chunks, 1) > 0.3:
        status = FAIL
        all_ok = False
        verdict = f"HIGH CORRUPTION ({corrupt}/{chunks} chunks)"
    elif avg_len < 200:
        status = WARN
        verdict = f"Chunks too small (avg {avg_len} chars) — data may be fragmented"
    else:
        status = PASS
        verdict = f"{chunks} clean chunks | Avg {avg_len} chars | Sections: {sections}"

    print(f"  {status} {ticker}: {verdict}")

print()
if all_ok:
    print("🟢 OVERALL: Database is HEALTHY. Data is clean and ready for querying.")
else:
    print("🔴 OVERALL: ISSUES DETECTED. Please re-run: python scripts/reingest_audit.py")

print("="*60 + "\n")
