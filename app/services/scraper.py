from bs4 import BeautifulSoup
from pathlib import Path
import ast
import json
from datetime import datetime, timezone
import requests
import re

folder = "data3" 

html_file = Path(__file__).parent.parent/"demo_data"/folder/"scrape.html"
script_file = Path(__file__).parent.parent/"demo_data"/folder/"script.txt"
enqueue = Path(__file__).parent.parent/"demo_data"/folder/"enqueue.json"
chat_json = Path(__file__).parent.parent/"demo_data"/folder/"chat_data.json"



def html_fetcher(url:str):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    # Force UTF-8. response.text often uses ISO-8859-1/cp1252 when the
    # header has no charset, which turns → / emoji into mojibake (â†’ , ðŸ‘‹).
    try:
        html = response.content.decode("utf-8")
    except UnicodeDecodeError:
        html = response.content.decode("utf-8", errors="replace")

    try:
        with open(html_file, 'w', encoding="utf-8") as file:
            file.write(html)
    except:
        return{
            "message":"file could not be loaded"
        }
        
    return{
        "status_code":response.status_code,
        "message":"file loaded successfully"
    }


def script_parser():
    with open(html_file, 'r', encoding="utf-8") as file:
        html_data = file.read()
    try:
        soup = BeautifulSoup(html_data, 'html.parser')
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.get_text()
            if "streamController.enqueue" in text:
                with open(script_file, 'w', encoding="utf-8") as file:
                    file.write(text)
                return text
    except:
        return{"some error"}


# extracting payload from script
def extract_payload():
    with open(script_file, "r", encoding="utf-8") as file:
        script = file.read()

    marker = "streamController.enqueue("
    
    start = script.find(marker)

    if start == -1:
        return "enqueue not found"

    # Find the first quote after enqueue(
    quote_start = start + len(marker)

    while quote_start < len(script) and script[quote_start].isspace():
        quote_start += 1

    quote = script[quote_start]

    if quote not in ["'", '"']:
        return "opening quote not found"

    payload_start = quote_start + 1

    # Find the matching closing quote
    i = payload_start

    while i < len(script):
        if script[i] == quote and script[i - 1] != "\\":
            break
        i += 1

    if i >= len(script):
        return "closing quote not found"

    payload = script[payload_start:i]

    if not payload:
        return "payload empty"

    payload = unescape_js_string(payload, quote)

    with open(enqueue, "w", encoding="utf-8") as file:
        file.write(payload)

    return "payload extracted"



def unescape_js_string(payload: str, quote: str) -> str:
   
    try:
        return ast.literal_eval(quote + payload + quote)
    except (SyntaxError, ValueError):
        unescaped = payload.encode("utf-8").decode("unicode_escape")
        return restore_utf8(unescaped)


def restore_utf8(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def json_load():
    with open(enqueue, 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data


def decode(data):

    cache = {}
    def resolve(index):
        if index in cache:
            return cache[index]
        value = data[index]
        if isinstance(value, dict):
            result = {}
            cache[index] = result
            for key, ref in value.items():
                # _122 means: use data[122] as the key
                if key.startswith("_"):
                    actual_key = resolve(int(key[1:]))
                else:
                    actual_key = key
                # positive integer means: reference to another index
                if isinstance(ref, int) and ref >= 0:
                    actual_value = resolve(ref)
                else:
                    actual_value = ref

                result[actual_key] = actual_value
            return result

        elif isinstance(value, list):
            result = []
            cache[index] = result

            for item in value:
                if isinstance(item, int) and item >= 0:
                    result.append(resolve(item))
                else:
                    result.append(item)
            return result
        else:
            cache[index] = value
            return value
    return resolve(0)


def get_conversation_data(decoded):

    loader_data = decoded.get("loaderData", {})
    route_data = loader_data.get(
        "routes/share.$shareId.($action)", {}
    )
    server_response = route_data.get("serverResponse", {})
    data = server_response.get("data", {})

    conversation_id = data.get("conversation_id")
    title = data.get("title")
    if isinstance(title, str):
        title = restore_utf8(title)
    mapping = data.get("mapping")

    return conversation_id, title, mapping



def get_messages(mapping):
    messages = []

    for nodeid, node in mapping.items():
        message = node.get("message")

        if message is None:
            continue

        role = message.get("author", {}).get("role")

        if role not in ["user", "assistant"]:
            continue

        content = message.get("content", {})
        parts = content.get("parts", [])

        # parts = [part for part in parts if part]
        if not parts:
            continue
        # text = "\n".join(str(part) for part in parts)

        content_block = []
        for part in parts:
            if not part:
                continue
            if isinstance(part, str):
                content_block.append({"type": "text", "text": restore_utf8(part)})

        if not content_block:
            continue


        messages.append({
            "id": message.get("id"),
            "role":role,
            "content":content_block,
            "timestamp":message.get("create_time")
        })

    return messages


def chat_scraper(url):

    html_fetcher(url)

    script_parser()

    extract_payload()

    data = json_load()

    decoded = decode(data)

    conversation_id, title, mapping = get_conversation_data(decoded)

    messages = get_messages(mapping)

    result = {
        "conversation_id":conversation_id,
        "platform":"chatgpt",
        "source_url":url,
        "title":title,
        "scraped_at":datetime.now(timezone.utc).isoformat(),
        "messages":messages
    }

    with open(chat_json, 'w', encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    return result

