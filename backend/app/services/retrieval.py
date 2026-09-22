import re

from rank_bm25 import BM25Okapi

from app.services.chroma import get_client, collection_name

TOP_SEMANTIC = 15
TOP_KEYWORD = 15
TOP_CANDIDATES = 10

# How many chunks are handed to the LLM per section. This is the single knob
# for retrieval depth. Raising it gives the document more source material, but
# the prompt still has to fit CONTEXT_TOKEN_LIMIT in app/services/llm.py, which
# trims the lowest-ranked chunks when the budget runs out - so raising this
# past what the budget allows has no effect.
FINAL_TOP_K = 5

SEMANTIC_WEIGHT = 0.65
KEYWORD_WEIGHT = 0.35

# reranker = CrossEncoder("BAAI/bge-reranker-base")

def tokenize(text):
    return re.findall(r"\b\w+\b", text.lower())


def normalize_scores(scores):
    if not scores:
        return {}

    minimum = min(scores.values())
    maximum = max(scores.values())

    if maximum == minimum:
        return {key: 1.0 for key in scores}

    return {
        key: (value - minimum) / (maximum - minimum)
        for key, value in scores.items()
    }


def retrieve_section( collection, query_embedding, query_text, top_k = FINAL_TOP_K ):

    semantic_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_SEMANTIC,
        include=["documents", "metadatas", "distances"]
    )
    ids = semantic_result["ids"][0]
    documents = semantic_result["documents"][0]
    distances = semantic_result["distances"][0]
    metadatas = semantic_result["metadatas"][0]

    semantic_scores = {}
    chunk_data = {}

    for i, chunk_id in enumerate(ids):

        semantic_scores[chunk_id] = (
            1 - distances[i]
        )

        chunk_data[chunk_id] = {
            "text": documents[i],
            "metadata": metadatas[i],
            "distance": distances[i]
        }

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    bm25 = BM25Okapi(
        tokenized_documents
    )

    query_tokens = tokenize(
        query_text
    )

    keyword_raw = bm25.get_scores(
        query_tokens
    )

    keyword_scores = {}

    for i, chunk_id in enumerate(ids):

        keyword_scores[chunk_id] = float(
            keyword_raw[i]
        )

    semantic_scores = normalize_scores(
        semantic_scores
    )

    keyword_scores = normalize_scores(
        keyword_scores
    )

    candidates = []

    for chunk_id in ids:

        semantic_score = semantic_scores.get(
            chunk_id,
            0.0
        )

        keyword_score = keyword_scores.get(
            chunk_id,
            0.0
        )

        hybrid_score = (
            SEMANTIC_WEIGHT * semantic_score
            +
            KEYWORD_WEIGHT * keyword_score
        )

        candidates.append({
            "chunk_id": chunk_id,
            "text": chunk_data[chunk_id]["text"],
            "metadata": chunk_data[chunk_id]["metadata"],
            "semantic_score": semantic_score,
            "keyword_score": keyword_score,
            "hybrid_score": hybrid_score
        })

    candidates.sort(
        key=lambda x: x["hybrid_score"],
        reverse=True
    )

    return candidates[:top_k]


def retrieve_data(conversation_id, docs_embed=None):
    if not conversation_id:
        return {}

    if not isinstance(docs_embed, dict) or not docs_embed:
        return {}

    try:
        client = get_client()
        collection = client.get_collection(name=collection_name(conversation_id))
    except Exception:
        return {}

    retrieved = {}

    for section, query in docs_embed.items():
        if not isinstance(query, dict):
            continue

        embedding = query.get("embedding")
        query_text = query.get("query_text") or ""

        if not embedding:
            continue

        try:
            retrieved[section] = retrieve_section(
                collection=collection,
                query_embedding=embedding,
                query_text=query_text,
                top_k=FINAL_TOP_K,
            )
        except Exception:
            retrieved[section] = []

    if not any(retrieved.values()):
        return {}

    return retrieved
