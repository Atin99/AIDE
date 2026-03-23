import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        if not os.path.exists(CHROMA_PATH):
            return None
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        try:
            _collection = client.get_collection("materials_papers")
        except Exception:
            return None
    return _collection


def retrieve(query: str, n_results: int = 5):
    try:
        model = _get_model()
        collection = _get_collection()
        if collection is None:
            return []
        embedding = model.encode(query).tolist()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, collection.count()),
        )
        output = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            output.append({"text": doc, "source": meta.get("source", ""),
                           "chunk": meta.get("chunk", 0)})
        return output
    except Exception as e:
        return []


def rag_available() -> bool:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        return os.path.exists(CHROMA_PATH)
    except ImportError:
        return False
