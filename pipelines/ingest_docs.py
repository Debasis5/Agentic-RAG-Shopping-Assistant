"""
Document ingestion pipeline for the ShopEasy Agentic RAG knowledge base.

Run once to load, chunk, embed and store documents:
    python pipelines/ingest_docs.py

Re-run whenever documents in data/docs/ are added or updated.
"""

import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION_NAME = "support_docs"


def load_documents() -> list[Document]:
    loader = PyPDFDirectoryLoader(DATA_DIR, extract_images=False)
    pages = loader.load()

    merged = defaultdict(lambda: {"text": ""})
    for page in pages:
        merged[page.metadata["source"]]["text"] += page.page_content + "\n"

    docs = []
    for src, val in merged.items():
        meta, clean_text = _parse_header(val["text"])
        meta["source"] = src
        docs.append(Document(page_content=clean_text, metadata=meta))

    print(f"[load] {len(docs)} documents loaded")
    return docs


def _parse_header(text: str) -> tuple[dict, str]:
    """Strip title, version, effective date and department from document header."""
    lines = text.strip().split("\n")
    meta = {"title": "", "version": "", "effective_date": "", "department": ""}
    consume = 0

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if i == 0:
            meta["title"] = line_stripped
            consume += 1
        elif re.match(r"Version\s+[\d.]+", line_stripped):
            version_match = re.search(r"Version\s+([\d.]+)", line_stripped)
            date_match = re.search(r"Effective Date:\s*(.+)", line_stripped)
            if version_match:
                meta["version"] = version_match.group(1)
            if date_match:
                meta["effective_date"] = date_match.group(1).strip()
            consume += 1
        elif "ShopEasy Customer Support" in line_stripped:
            meta["department"] = "ShopEasy Customer Support"
            consume += 1
        else:
            break

    return meta, "\n".join(lines[consume:]).strip()


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=650,
        chunk_overlap=0,
        separators=[
            r"\n(?=\d+\. )",  # split before numbered sections: 1. , 2. , 3. etc.
            "\n\n",
            "\n",
        ],
        is_separator_regex=True,
    )
    chunks = splitter.split_documents(docs)
    print(f"[chunk] {len(chunks)} chunks created")
    return chunks


def ingest(chunks: list[Document]) -> None:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
    )
    count = vectorstore._collection.count()
    print(f"[ingest] {count} chunks ingested into ChromaDB")
    print(f"[ingest] persisted to: {os.path.abspath(CHROMA_DIR)}")


if __name__ == "__main__":
    print("Starting document ingestion pipeline...\n")
    docs = load_documents()
    chunks = chunk_documents(docs)
    ingest(chunks)
    print("\nIngestion complete.")
