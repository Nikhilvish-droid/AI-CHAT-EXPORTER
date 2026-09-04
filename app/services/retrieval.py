import json
import chromadb
from pathlib import Path

folder = "data7"
docs_data = Path(__file__).parent.parent/"demo_data"/folder/"docs_embed.json"
retrieved_file = Path(__file__).parent.parent/"demo_data"/folder/"retrieved_data.json"
chroma_data = Path(__file__).parent.parent/"chroma_data"


def retrieve_data(conversation_id):

    with open(docs_data, 'r', encoding="utf-8") as file:
        docs_embed = json.load(file)
    
    client = chromadb.PersistentClient(path=chroma_data)
    collection = client.get_or_create_collection(
        name= f"conv-{conversation_id}",
        metadata={"hnsw:space": "cosine"}
    )

    retrieved = {}

    for section, query in docs_embed.items():
        embedding = query.get("embedding")

        result = collection.query(
            query_embeddings = [embedding],
            n_results=3
        )

        retrieved[section] = result
    
    with open(retrieved_file, 'w', encoding="utf-8") as file:
        json.dump(retrieved, file, ensure_ascii=False, indent=4)

    return retrieved





# def getconversation_id():
#     embed = Path(__file__).parent.parent/"demo_data"/folder/"embed.json"
#     with open(embed, 'r', encoding="utf-8") as file:
#         data = json.load(file)
#     conversation_id = data[0].get("conversation_id")

#     return conversation_id
#     

