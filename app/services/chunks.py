import json
from pathlib import Path
import json
import re

folder = "data8"
chat = Path(__file__).parent.parent/"demo_data"/folder/"chat_data.json"
chunks_file = Path(__file__).parent.parent/"demo_data"/folder/"chunks.json"


def clean_embedtext(text:str):
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"__", "", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(
        r"[\U0001F300-\U0001FAFF"
        r"\U00002600-\U000027BF"
        r"\U0001F1E6-\U0001F1FF]+",
        "",
        text
    )
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text



def create_chunks(data):
    max_char = 1000
    chunks = []
    # with open(chat, 'r', encoding="utf-8") as file:
    #     data = json.load(file)

    messages = data["messages"]
    conversation_id = data["conversation_id"]

    i = 0
    while i < len(messages) - 1:
        user = messages[i]
        assistant = messages[i+1]

        if user["role"] == "user" or assistant["role"] == "assistant":
            user_text = user["content"][0]["text"]
            assistant_text = assistant["content"][0]["text"]

            combined_text = f" User: {user_text} \n\n assistant: {assistant_text} "

            if len(combined_text) <= max_char:

                embed_text = clean_embedtext(combined_text)

                chunks.append({
                    "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                    "conversation_id": conversation_id,
                    "type": "text",
                    "text": combined_text,
                    "embedded_text": embed_text,
                    "verbatim": False,
                    "source_message_ids": [
                        user["id"],
                        assistant["id"]
                    ],
                    "roles_included": [
                        "user",
                        "assistant"
                    ],
                    "order_index": len(chunks),
                    "char_count": len(combined_text)
                })

            else:
                overlap = 100
                onlyassistant = False
                for start in range(0, len(combined_text), max_char - overlap):

                    chunk_text = combined_text[start:start + max_char]
                    embed_text = clean_embedtext(chunk_text)

                    if onlyassistant:
                        roles_included = ["assistant"]
                    else :
                        roles_included = ["user", "assistant"]

                    chunks.append({
                        "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                        "conversation_id": conversation_id,
                        "type": "text",
                        "text": chunk_text,
                        "embedded_text": embed_text,
                        "verbatim": False,
                        "source_message_ids": [
                            user["id"],
                            assistant["id"]
                        ],
                        "roles_included": roles_included,
                        "order_index": len(chunks),
                        "char_count": len(chunk_text)
                    })

                    onlyassistant = True
            i += 2

        else:
            i += 1

    with open(chunks_file, 'w', encoding="utf-8") as file:
        data = json.dump(chunks, file, indent = 4, ensure_ascii=False)

    return{
        "ok":True,
        "message":"chunks created successfully",
        "chunks":chunks
    }


# with open(chat, 'r', encoding="utf-8") as file:
#     data = json.load(file)

# print(create_chunks(data))