# bypass the parsed schema into the chromadb
# building up vector and keyword indexing 
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from config import CHROMA_PATH, OPENAI_API_KEY
from parser import parse_db

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def build_index(schema_entries: List[Dict[str, Any]]):
    """
    build two chromadb collections:
    1. vector_index: use openai embedding for semantic search
    2. keyword_index: store original text, use for BM25 search
    """

    client = get_chroma_client()
    for name in ["vector_index", "keyword_index"]:
        try:
            client.delete_collection(name)
        except Exception:
            pass

    # by default use openai, in deployment mode
    # openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    #     api_key=OPENAI_API_KEY,
    #     model_name="text-embedding-3-small"
    # )

    # in dev mode, use this free one from chroma
    local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    vector_col = client.create_collection(
        name="vector_index",
        embedding_function=local_ef
    )

    # keyword search
    keyword_col = client.create_collection(
        name="keyword_index"
    )

    # multi write in
    ids = [e["field_id"] for e in schema_entries]
    field_descs = [e["field_description"] for e in schema_entries]
    keyword_texts = [e["keyword_text"] for e in schema_entries]
    
    metadatas = [
        {
            "database_name": e["database_name"],
            "table_name": e["table_name"],
            "field_name": e["field_name"],
            "field_type": e["field_type"],
            "field_description": e["field_description"],
            "keyword_text": e["keyword_text"],
        }
        for e in schema_entries
    ]

    # for field_descs to embedding
    vector_col.add(
        ids=ids,
        documents=field_descs,
        metadatas=metadatas
    )

    keyword_col.add(
        ids=ids,
        documents=keyword_texts,
        metadatas=metadatas
    )

    print(f"Indexed {len(ids)} fields into ChromaDB")
    print(f"vector_index: {vector_col.count()} documents")
    print(f"keyword_index: {keyword_col.count()} documents")

if __name__ == "__main__":
    entries = parse_db()
    build_index(entries)




