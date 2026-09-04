import chromadb
from pathlib import Path
import json


folder = "data7"
embed_json = Path(__file__).parent.parent/"demo_data"/folder/"embed.json"
chromapath = Path(__file__).parent.parent/"chroma_data"

def add_chunks_to_chroma(data):

    # with open(embed_json, 'r', encoding="utf-8") as file:
    #     data = json.load(file)
    conversation_id = data[0].get("conversation_id")

    client = chromadb.PersistentClient(path=chromapath)
    collection = client.get_or_create_collection(
        name = f"conv-{conversation_id}",
        metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[c["chunk_id"] for c in data],
        embeddings=[c["embedding"] for c in data],
        documents= [ c["embedded_text"] for c in data],
        metadatas=[{
            "conversation_id": c["conversation_id"],
            "type": c["type"],
            "verbatim": c["verbatim"],
            "order_index": c["order_index"],
            "char_count": c["char_count"],
            "roles_included": ",".join(c["roles_included"]),
            "source_message_ids": ",".join(c["source_message_ids"]),
        } for c in data ]
    )

    return {
        "ok":True,
        "message":"successfully stored in chroma",
        "conversation_id":conversation_id
    }

