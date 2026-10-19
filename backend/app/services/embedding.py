import threading

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SECTION_QUERIES = {
    "overview": "what is this conversation about, overall goal, main topic, background and context",
    "key_decisions": "decisions made, choices agreed upon, conclusions reached, important decisions",
    "problems_solutions": "problems discussed, errors encountered, challenges, solutions, fixes, troubleshooting",
    "technical_details": "technical concepts, technologies, tools, code, implementation details, methods discussed",
}

_model = None
_model_lock = threading.Lock()


def get_model():
    global _model

    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)

    return _model


def get_docs_embed():
    model = get_model()
    result = {}

    for section, query in SECTION_QUERIES.items():
        vector = model.encode(query, normalize_embeddings=True)
        result[section] = {"query_text": query, "embedding": vector.tolist()}

    return result


def create_embeddings(chunk_data):
    if not isinstance(chunk_data, list) or not chunk_data:
        return {"ok": False, "message": "create_embeddings: no chunks supplied", "data": []}

    try:
        model = get_model()
    except Exception as e:
        return {"ok": False, "message": f"create_embeddings: model unavailable: {e}", "data": []}

    embedded = []

    for chunk in chunk_data:
        embed_text = (chunk.get("embedded_text") or "").strip()

        if not embed_text:
            embed_text = (chunk.get("text") or "").strip()

        if not embed_text:
            continue

        try:
            vector = model.encode(embed_text, normalize_embeddings=True)
        except Exception as e:
            return {"ok": False, "message": f"create_embeddings: encoding failed: {e}", "data": []}

        chunk["embedding"] = vector.tolist()
        embedded.append(chunk)

    if not embedded:
        return {
            "ok": False,
            "message": "create_embeddings: every chunk was empty after cleaning",
            "data": [],
        }

    try:
        docs_embed = get_docs_embed()
    except Exception as e:
        return {"ok": False, "message": f"create_embeddings: section queries failed: {e}", "data": []}

    return {
        "ok": True,
        "data": embedded,
        "docs_embed": docs_embed,
        "skipped": len(chunk_data) - len(embedded),
    }
