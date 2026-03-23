import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        i += size - overlap
    return chunks


def extract_text_from_pdf(pdf_path):
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        pass
    try:
        import PyPDF2
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        pass
    return ""


def build_index(papers_dir=None):
    if not RAG_AVAILABLE:
        print("RAG indexing requires: pip install chromadb sentence-transformers")
        return None

    if papers_dir is None:
        papers_dir = os.path.join(os.path.dirname(__file__), "papers")
    os.makedirs(papers_dir, exist_ok=True)

    pdfs = [f for f in os.listdir(papers_dir) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"  No PDFs found in {papers_dir}")
        print("  Place PDF papers there and re-run.")
        return None

    print(f"  Loading embedding model (all-MiniLM-L6-v2, 90MB)...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name="materials_papers",
        metadata={"hnsw:space": "cosine"}
    )

    total_chunks = 0
    for pdf_file in pdfs:
        pdf_path = os.path.join(papers_dir, pdf_file)
        print(f"  Indexing {pdf_file}...")
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"    (no text extracted — skipping)")
            continue
        chunks = chunk_text(text)
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()
        ids = [f"{pdf_file}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": pdf_file, "chunk": i} for i in range(len(chunks))]
        collection.add(documents=chunks, embeddings=embeddings,
                        ids=ids, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"    {len(chunks)} chunks indexed")

    print(f"\n  Index complete: {total_chunks} chunks from {len(pdfs)} papers")
    print(f"  Stored at: {CHROMA_PATH}")
    return collection


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    args = ap.parse_args()
    build_index(args.dir)
