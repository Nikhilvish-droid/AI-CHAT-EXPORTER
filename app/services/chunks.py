import json
from pathlib import Path
import json

folder = "data3"
chat = Path(__file__).parent.parent/"demo_data"/folder/"chat_data.json"
chunks_file = Path(__file__).parent.parent/"demo_data"/folder/"chunks.json"





def create_chunks():
    max_char = 1000
    chunks = []
    with open(chat, 'r', encoding="utf-8") as file:
        data = json.load(file)

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
                 chunks.append({
                    "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                    "conversation_id": conversation_id,
                    "type": "text",
                    "text": combined_text,
                    "embedded_text": "",
                    "verbatim": True,
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
                for start in range(0, len(combined_text), max_char - overlap):

                    chunk_text = combined_text[start:start + max_char]

                    chunks.append({
                        "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                        "conversation_id": conversation_id,
                        "type": "text",
                        "text": chunk_text,
                        "embedded_text": "",
                        "verbatim": True,
                        "source_message_ids": [
                            user["id"],
                            assistant["id"]
                        ],
                        "roles_included": [
                            "user",
                            "assistant"
                        ],
                        "order_index": len(chunks),
                        "char_count": len(chunk_text)
                    })

            i += 2

        else:
            i += 1

    with open(chunks_file, 'w', encoding="utf-8") as file:
            data = json.dump(chunks, file, indent = 4, ensure_ascii=False)

    return{
        "message":"chunks created successfully"
    }

print(create_chunks())