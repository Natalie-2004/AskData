import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_PATH

def get_vector_collections():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection("vector_index", embedding_function=local_ef)

def get_keyword_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection("keyword_index")

"""
dynamically adjust top-k based on number of keywords
fewer keywords = cast wider net

PROD RULE:
1. The number of keywords is 1-2:
   Recruit the top 30 for each route, and expand the coverage area. 
2. The number of keywords is 3 to 5:
   Recalls the top 20 for each route 
3. If the number of keywords exceeds 5:
   Recall the top 10 for each path, avoiding excessive noise in the recall results.
"""
def get_dynamic_top_k(keyword_count: int) -> int:
    if keyword_count <= 2:
        # small db so lower than original
        return 6
    if keyword_count <= 5:
        return 4
    
    return 2

# sematic vector search using local embedding model.
# good at fuzzy matching, finding words with similar meanings
def vector_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    col = get_vector_collections()
    # cap topk at collection size to avoid chroma err
    top_k = min(top_k, col.count())
    res = col.query(query_texts=[query], n_results=top_k)

    rows = []
    for rank, (doc_id, metadata, dist) in enumerate(zip(
        res["ids"][0],
        res["metadatas"][0],
        res["distances"][0]
    ), start=1):
        rows.append({
            "rank": rank,
            "score": 1 - dist,
            "source": "vector",
            "field_id": doc_id,
            **metadata
        })
    return rows

# the bm25 keyword search over stored core keyword text
# as long as the user mentions the exact table name or proper noun, it can instantly identify it.
def keyword_search(keywords: List[str], top_k: int) -> List[Dict[str, Any]]:
    col = get_keyword_collection()
    all_docs = col.get(include=["documents", "metadatas"])
    doc_ids = all_docs["ids"]
    docs = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    tokenised = []
    for doc in docs:
        tokenised.append(doc.lower().split())
    bm25 = BM25Okapi(tokenised)

    all_res = []
    for k in keywords:
        query_tokens = k.lower().split()
        scores = bm25.get_scores(query_tokens)

        ranked_ind = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        for r, i in enumerate(ranked_ind, start=1):
            if scores[i] > 0:
                all_res.append({
                    "rank": r,
                    "score": float(scores[i]),
                    "source": "keyword",
                    "keyword": k,
                    "field_id": doc_ids[i],
                    **metadatas[i]
                })

    return all_res

"""
Reciprocal Rank Fusion(rrf)
combines keyword and vector results by ranking, not raw scores.
avoids the problem of different score scales
"""
def rrf_fusion(
        keyword_res: List[Dict[str, Any]],
        vector_res: List[Dict[str, Any]],
        rrf_k: int = 60
) -> List[Dict[str, Any]]:
    rrf_scores: Dict[str, float] = {}
    field_data: Dict[str, Dict] = {}

    for res in keyword_res:
        fid = res["field_id"]
        rank = res["rank"]
        rrf_scores[fid] = rrf_scores.get(fid, 0) + 1 / (rrf_k + rank)
        field_data[fid] = res

    for res in vector_res:
        fid = res["field_id"]
        rank = res["rank"]
        rrf_scores[fid] = rrf_scores.get(fid, 0) + 1 / (rrf_k + rank)
        if fid not in field_data:
            field_data[fid] = res

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    fused = []
    for rank, fid in enumerate(sorted_ids, start=1):
        item = field_data[fid].copy()
        item["rrf_score"] = rrf_scores[fid]
        item["rrf_rank"] = rank
        fused.append(item)

    return fused

def hybrid_retrieve(
        query: str,
        keywords: List[str],
        final_top_k: int = 6
) -> Dict[str, Any]:
    top_k = get_dynamic_top_k(len(keywords))
    keyword_res = keyword_search(keywords, top_k)
    vector_res = vector_search(query, top_k)
    fused = rrf_fusion(keyword_res, vector_res)

    return {
        "results": fused[:final_top_k],
        "dynamic_top_k": top_k
    }

if __name__ == "__main__":
    from backend.retrieval.keyword_extractor import extract_keywords

    test_queries = [
        "Which users have interest rate higher than 3.5?",
        "What is the total trade count for each user?"
    ]

    for q in test_queries:
        keywords = extract_keywords(q)
        print(f"\nQuery:    {q}")
        print(f"Keywords: {keywords}")

        res = hybrid_retrieve(query=q, keywords=keywords)
        print(f"Top results:")
        for item in res["results"]:
            print(
                f"  [{item['rrf_rank']}] "
                f"{item['table_name']}.{item['field_name']} "
                f"(rrf_score: {item['rrf_score']:.4f}, source: {item['source']})"
            )


