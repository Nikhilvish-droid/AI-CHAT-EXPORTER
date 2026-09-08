from bs4 import BeautifulSoup
from pathlib import Path
import ast
import json
from datetime import datetime, timezone
import re
from curl_cffi import requests as cffi_requests

folder = "data8" 

html_file = Path(__file__).parent.parent/"demo_data"/folder/"scrape.html"
script_file = Path(__file__).parent.parent/"demo_data"/folder/"script.txt"
enqueue = Path(__file__).parent.parent/"demo_data"/folder/"enqueue.json"
chat_json = Path(__file__).parent.parent/"demo_data"/folder/"chat_data.json"
decoded_json = Path(__file__).parent.parent/"demo_data"/folder/"decoded.txt"


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def html_fetcher(url: str):
    try:
        r = cffi_requests.get(url, impersonate="chrome124", timeout=20)
    except Exception as e:
        return _fail(f"html_fetcher: request failed: {e}")

    if r.status_code != 200:
        return _fail(f"html_fetcher: HTTP {r.status_code} for URL {url}")

    try:
        html = r.content.decode("utf-8")
    except UnicodeDecodeError:
        html = r.content.decode("utf-8", errors="replace")

    if not html.strip():
        return _fail("html_fetcher: empty html returned")

    try:
        with open(html_file, "w", encoding="utf-8") as file:
            file.write(html)
    except Exception as e:
        return _fail(f"html_fetcher: could not write html file: {e}")

    return _ok(html)


def script_parser(html_data):
    # with open(html_file, 'r', encoding="utf-8") as file:
    #     html_data = file.read()
    if not isinstance(html_data, str) or not html_data:
        return _fail("script_parser: invalid html_data")

    try:
        soup = BeautifulSoup(html_data, 'html.parser')
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.get_text()
            if "streamController.enqueue" in text:
                with open(script_file, 'w', encoding="utf-8") as file:
                    file.write(text)
                return _ok(text)
    except Exception as e:
        return _fail(f"script_parser: failed to parse html: {e}")

    return _fail("script_parser: streamController.enqueue script not found")


# extracting payload from script
def extract_payload(script):
    # with open(script_file, "r", encoding="utf-8") as file:
    #     script = file.read()
    if not isinstance(script, str) or not script:
        return _fail("extract_payload: invalid script")

    marker = "streamController.enqueue("
    
    start = script.find(marker)

    if start == -1:
        return _fail("extract_payload: enqueue not found")

    # Find the first quote after enqueue(
    quote_start = start + len(marker)

    while quote_start < len(script) and script[quote_start].isspace():
        quote_start += 1

    quote = script[quote_start]

    if quote not in ["'", '"']:
        return _fail("extract_payload: opening quote not found")

    payload_start = quote_start + 1

    # Find the matching closing quote
    i = payload_start

    while i < len(script):
        if script[i] == quote and script[i - 1] != "\\":
            break
        i += 1

    if i >= len(script):
        return _fail("extract_payload: closing quote not found")

    payload = script[payload_start:i]

    if not payload:
        return _fail("extract_payload: payload empty")

    payload = unescape_js_string(payload, quote)

    with open(enqueue, "w", encoding="utf-8") as file:
        file.write(payload)

    if not payload.strip():
        return _fail("extract_payload: payload extracted but empty")

    return _ok(payload)



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


# def json_load():
#     with open(enqueue, 'r', encoding="utf-8") as file:
#         data = json.load(file)
#     return data


def decode(data):
    try:
        if not isinstance(data, list) or not data:
            return _fail("decode: payload JSON is not a non-empty list")

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
                    if isinstance(key, str) and key.startswith("_"):
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

        decoded = resolve(0)
        if not isinstance(decoded, dict):
            return _fail("decode: decoded root is not a dict")



        return _ok(decoded)
    except Exception as e:
        return _fail(f"decode: failed: {e}")


def get_conversation_data(decoded):
    if not isinstance(decoded, dict):
        return _fail("get_conversation_data: decoded is not a dict")

    try:
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

        if not conversation_id:
            return _fail("get_conversation_data: conversation_id missing")
        if not isinstance(mapping, dict):
            return _fail("get_conversation_data: mapping is not a dict")

        return _ok((conversation_id, title, mapping))
    except Exception as e:
        return _fail(f"get_conversation_data: failed: {e}")



def get_messages(mapping):
    if not isinstance(mapping, dict):
        return _fail("get_messages: mapping is not a dict")

    try:
        messages = []

        for nodeid, node in mapping.items():
            if not isinstance(node, dict):
                continue
            message = node.get("message")

            if message is None or not isinstance(message, dict):
                continue

            role = message.get("author", {}).get("role")

            if role not in ["user", "assistant"]:
                continue

            content = message.get("content", {})
            parts = content.get("parts", [])

            # parts = [part for part in parts if part]
            if not parts or not isinstance(parts, list):
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
                "role": role,
                "content": content_block,
                "timestamp": message.get("create_time")
            })

        return _ok(messages)
    except Exception as e:
        return _fail(f"get_messages: failed: {e}")


def chat_scraper(url):

    html_res = html_fetcher(url)
    if not html_res.get("ok"):
        return {"ok": False, "message": html_res.get("message", "html_fetcher failed")}
    html = html_res["value"]

    script_res = script_parser(html)
    if not script_res.get("ok"):
        return {"ok": False, "message": script_res.get("message", "script_parser failed")}
    script = script_res["value"]

    payload_res = extract_payload(script)
    if not payload_res.get("ok"):
        return {"ok": False, "message": payload_res.get("message", "extract_payload failed")}
    payload = payload_res["value"]

    try:
        payload_data = json.loads(payload)
    except Exception as e:
        return {"ok": False, "message": f"chat_scraper: payload JSON parse failed: {e}"}

    decoded_res = decode(payload_data)
    if not decoded_res.get("ok"):
        return {"ok": False, "message": decoded_res.get("message", "decode failed")}
    decoded = decoded_res["value"]

    conv_res = get_conversation_data(decoded)
    if not conv_res.get("ok"):
        return {"ok": False, "message": conv_res.get("message", "get_conversation_data failed")}
    conversation_id, title, mapping = conv_res["value"]

    messages_res = get_messages(mapping)
    if not messages_res.get("ok"):
        return {"ok": False, "message": messages_res.get("message", "get_messages failed")}
    messages = messages_res["value"]

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

    return {"data": result, "ok": True}
