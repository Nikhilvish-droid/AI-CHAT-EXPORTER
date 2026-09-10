import json
from curl_cffi import requests as cffi_request
import json
from datetime import datetime, timezone
import time
from pathlib import Path

# share_url = "https://claude.ai/share/5a147e2f-61a6-44e8-9ec6-31f8d32a6a13"


folder = "1" 
app_dir = Path(__file__).parent.parent.parent
platform = "claude"
chat_data = app_dir/"demo_data"/platform/folder/"chat_data.json"
scrape_data = app_dir/"demo_data"/platform/folder/"fetch_data.json"


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def fetch_data(url):

    share_id = url.split('/')[-1]
    api_url = f"https://claude.ai/api/chat_snapshots/{share_id}?rendering_mode=messages&render_all_tools=true"

    try:
        response = cffi_request.get(api_url, impersonate="chrome124", timeout=15)
        
        if response.status_code == 200:
            parsed_json = response.json()
            
            with open(scrape_data, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=4, ensure_ascii=False)

            return _ok(parsed_json)
        else:
            return _fail(f"Could not scrape data, status code: {response.status_code}")
            
    except Exception as e:
        return _fail(f"Request failed: {str(e)}")

def get_chat_messages(data):
    messages = []
    chat_messages = data.get("chat_messages")

    for message in chat_messages:
        message_id = message.get("uuid")
        role = message.get("sender")
        if role == "human": role = "user"

        contents = message.get("content", [])
        timestamp = message.get("created_at", time.time())

        text_content = []
        all_text = ""
        for content in contents:
            type = content.get("type")
            if type == "text":
                text = content.get("text")
                all_text += ". " + text
            else:
                continue
            
        text_content.append({
            "type":type,
            "text":all_text
        })
        

        if role == "user" or role == "assistant":
            
            messages.append({
                "id":message_id,
                "role":role,
                "content":text_content,
                "timestamp": timestamp
            })
    return messages

def convert_data_to_scheme(data, url, messages):

    json_schema = {
        "conversation_id": data.get("conversation_uuid"),
        "platform":"claude",
        "source_url":url,
        "title": data.get("snapshot_name"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "messages":messages
    }
    chat_data.parent.mkdir(parents=True, exist_ok=True)

    with open(chat_data, 'w', encoding="utf-8") as f:
        json.dump(json_schema, f, indent=2, ensure_ascii=False)

    return json_schema



def load_claude_chat(url):

    chat_response = fetch_data(url)

    if(chat_response.get("ok")):
        data = chat_response.get("value")
    else:
        return "could not scrape url"

    messages = get_chat_messages(data)

    formatted_data = convert_data_to_scheme(data, url, messages)

    print("Data successfully loaded and stored in JSON.")
    return _ok(formatted_data)


if __name__ == "__main__":

    share_url = "https://claude.ai/share/087cf7b8-a6bd-4a6f-98a7-bba5a332c58f"
    load_claude_chat(share_url)