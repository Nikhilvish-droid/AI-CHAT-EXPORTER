from sentence_transformers import SentenceTransformer
from pathlib import Path
import json

folder = "1"
app_dir = Path(__file__).parent.parent
platform = "gemini"

embeddings = app_dir/"demo_data"/platform/folder/"embed.json"
docs_embed = app_dir/"demo_data"/platform/folder/"docs_embed.json"

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def create_embeddings(chunk_data):
    # with open(chunks, 'r', encoding="utf-8") as file:
    #     chunk_data = json.load(file)


    for chunk in chunk_data:
        embed_text = chunk.get("embedded_text", "").strip()

        if not embed_text:
            continue
        
        embedding = model.encode(embed_text, normalize_embeddings=True)

        chunk["embedding"] = embedding.tolist()

    with open(embeddings, 'w', encoding="utf-8")as file:
        json.dump(chunk_data, file, indent=4, ensure_ascii=False)

    get_docs_embed()

    return{
        "ok":True,
        "data":chunk_data
    }

# print(create_embeddings())
def get_docs_embed():

    queries = {
        "overview": "what is this conversation about, overall goal, main topic, background and context",
        
        "key_decisions": "decisions made, choices agreed upon, conclusions reached, important decisions",
        
        "problems_solutions": "problems discussed, errors encountered, challenges, solutions, fixes, troubleshooting",
        
        "technical_details": "technical concepts, technologies, tools, code, implementation details, methods discussed"
    }

    result = {}

    for section, query in queries.items():

        vector = model.encode(query, normalize_embeddings= True)
        result[section] = {"query_text":query, "embedding":vector.tolist()}

    with open(docs_embed, 'w', encoding="utf-8") as file:
        json.dump(result, file , indent=4, ensure_ascii=False)

    return "success"


# print(get_docs_embed())
    

    

    