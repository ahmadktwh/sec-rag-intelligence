import logging
import re
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Setup Logging
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Processes raw SEC filings (HTML) into clean, chunked text for vector storage.
    """
    
    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 400):
        """
        Initialize with larger chunks to capture full financial tables.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def clean_html(self, html_content: str) -> str:
        """
        Cleans SEC HTML by removing scripts, styles, and excessive whitespace.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'head', 'title', 'meta', '[document]']):
            tag.decompose()
            
        # Extract text with newlines to preserve table structure
        text = soup.get_text(separator='\n')
        
        # Clean excessive newlines but keep basic structure
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text

    def process_filing(self, file_path: Path, metadata: Dict) -> List[Document]:
        """
        Reads a filing file, cleans it, and splits it into chunked LangChain Documents.
        """
        try:
            logger.info(f"Processing filing: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            clean_text = self.clean_html(html_content)
            
            if not clean_text:
                logger.warning(f"No text extracted from {file_path}")
                return []
            
            # Identify major sections for better metadata
            # Item 1: Business, Item 7: MD&A, Item 8: Financials
            section_markers = {
                "Item 1": ["item 1.", "item 1 - business"],
                "Item 7": ["item 7.", "item 7 - management's discussion"],
                "Item 8": ["item 8.", "item 8 - financial statements"]
            }
            
            # Split into chunks
            chunks = self.text_splitter.split_text(clean_text)
            
            # Create LangChain Document objects with metadata
            documents = []
            current_section = "General"
            
            for i, chunk in enumerate(chunks):
                # Simple heuristic to update section context
                lower_chunk = chunk.lower()[:500]
                for section_name, markers in section_markers.items():
                    if any(marker in lower_chunk for marker in markers):
                        current_section = section_name
                        break
                
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "section": current_section, # Tagged section
                        "source": file_path.name
                    }
                )
                documents.append(doc)
            
            logger.info(f"Successfully processed {file_path} into {len(documents)} chunks (Detected sections).")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing filing {file_path}: {e}")
            return []

if __name__ == "__main__":
    # Test the processor
    logging.basicConfig(level=logging.INFO)
    processor = DocumentProcessor()
    
    # Use one of the downloaded files from Task 3
    raw_dir = Path("data/raw_filings")
    test_files = list(raw_dir.glob("AAPL_*.htm"))
    
    if test_files:
        test_file = test_files[0]
        test_meta = {"ticker": "AAPL", "filing_type": "10-K", "year": "2025"}
        docs = processor.process_filing(test_file, test_meta)
        
        if docs:
            print(f"\n[TEST] Processed {len(docs)} chunks.")
            print(f"[TEST] First chunk preview: {docs[0].page_content[:200]}...")
            print(f"[TEST] Metadata: {docs[0].metadata}")
    else:
        print("No test files found. Run edgar_fetcher.py first.")
