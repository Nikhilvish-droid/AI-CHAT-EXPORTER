from pathlib import Path

import chromadb


app_dir = Path(__file__).parent.parent
chromapath = app_dir / "chroma_data"


def collection_name(conversation_id):
    return f"conv-{conversation_id}"


def get_client():
    chromapath.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(chromapath))


def add_chunks_to_chroma(data):
    if not isinstance(data, list) or not data:
        return {"ok": False, "message": "add_chunks_to_chroma: no embedded chunks supplied"}

    usable = [c for c in data if c.get("embedding") and c.get("chunk_id")]

    if not usable:
        return {"ok": False, "message": "add_chunks_to_chroma: no chunk carried an embedding"}

    conversation_id = usable[0].get("conversation_id")

    if not conversation_id:
        return {"ok": False, "message": "add_chunks_to_chroma: chunks have no conversation_id"}

    try:
        client = get_client()

        collection = client.get_or_create_collection(
            name=collection_name(conversation_id),
            metadata={"hnsw:space": "cosine"},
        )

        collection.upsert(
            ids=[c["chunk_id"] for c in usable],
            embeddings=[c["embedding"] for c in usable],
            documents=[c.get("embedded_text") or c.get("text") or "" for c in usable],
            metadatas=[{
                "conversation_id": str(c.get("conversation_id") or ""),
                "type": str(c.get("type") or "text"),
                "verbatim": bool(c.get("verbatim")),
                "order_index": int(c.get("order_index") or 0),
                "char_count": int(c.get("char_count") or 0),
                "roles_included": ",".join(c.get("roles_included") or []),
                "source_message_ids": ",".join(str(i) for i in (c.get("source_message_ids") or [])),
            } for c in usable],
        )
    except Exception as e:
        return {"ok": False, "message": f"add_chunks_to_chroma: {e}"}

    return {
        "ok": True,
        "message": "successfully stored in chroma",
        "conversation_id": conversation_id,
        "stored": len(usable),
    }
