from bs4 import BeautifulSoup
from pathlib import Path
import ast
import json
from datetime import datetime, timezone
import re
from curl_cffi import requests as cffi_requests

from app.services import assets as assetlib

app_dir = Path(__file__).parent.parent.parent
platform = "chatgpt"

assets_dir = app_dir/"storage"/"assets"/platform

KEEP_CONTENT_TYPES = {"text", "multimodal_text"}

ENQUEUE_MARKER = "streamController.enqueue("

# Cloudflare stalls older browser fingerprints, so try newer ones first and
# fall back instead of failing the whole request on one stale profile.
IMPERSONATE_PROFILES = ("chrome131", "firefox", "chrome124")

ASSET_PART_TYPES = {
    "image_asset_pointer": "image",
    "audio_asset_pointer": "audio",
    "video_container_asset_pointer": "video",
    "file_asset_pointer": "file",
}


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def html_fetcher(url: str):
    problem = "no browser profile accepted"

    for profile in IMPERSONATE_PROFILES:
        try:
            r = cffi_requests.get(url, impersonate=profile, timeout=20)
        except Exception as e:
            problem = f"request failed as {profile}: {e}"
            continue

        if r.status_code != 200:
            problem = f"HTTP {r.status_code} for URL {url} as {profile}"
            continue

        try:
            html = r.content.decode("utf-8")
        except UnicodeDecodeError:
            html = r.content.decode("utf-8", errors="replace")

        if not html.strip():
            problem = f"empty html returned as {profile}"
            continue

        return _ok(html)

    return _fail(f"html_fetcher: {problem}")


def script_parser(html_data):
    if not isinstance(html_data, str) or not html_data:
        return _fail("script_parser: invalid html_data")

    try:
        soup = BeautifulSoup(html_data, 'html.parser')

        # The share page streams its data as several enqueue() calls, and they
        # are not always in the same script tag, so keep every one of them.
        scripts = [
            text
            for text in (script.get_text() for script in soup.find_all("script"))
            if ENQUEUE_MARKER in text
        ]
    except Exception as e:
        return _fail(f"script_parser: failed to parse html: {e}")

    if not scripts:
        return _fail("script_parser: streamController.enqueue script not found")

    return _ok(scripts)


def read_js_string(script, index):
    """Read one quoted JS string starting at or after ``index``.

    Returns (decoded_text, position_after_the_string). Escapes are skipped two
    characters at a time so an escaped backslash right before the closing quote
    (``"...\\\\"``) does not end the string early.
    """

    while index < len(script) and script[index].isspace():
        index += 1

    if index >= len(script) or script[index] not in ("'", '"', "`"):
        return None, index

    quote = script[index]
    body_start = index + 1
    i = body_start

    while i < len(script):
        char = script[i]

        if char == "\\":
            i += 2
            continue

        if char == quote:
            return unescape_js_string(script[body_start:i], quote), i + 1

        i += 1

    return None, len(script)


def enqueue_chunks(scripts):
    """Collect the argument of every streamController.enqueue() call, in order."""

    chunks = []

    for script in scripts:
        position = 0

        while True:
            found = script.find(ENQUEUE_MARKER, position)

            if found == -1:
                break

            text, position = read_js_string(script, found + len(ENQUEUE_MARKER))

            if position <= found:
                position = found + len(ENQUEUE_MARKER)

            if text and text.strip():
                chunks.append(text)

    return chunks


def parse_chunk(chunk):
    """Parse one enqueue chunk into the JSON list it carries, if it carries one.

    Chunks can be prefixed with a stream id such as ``P627:`` before the JSON.
    """

    start = chunk.find("[")

    if start == -1:
        return None

    try:
        data = json.loads(chunk[start:])
    except (json.JSONDecodeError, ValueError):
        return None

    return data if isinstance(data, list) and data else None


# extracting payload from script
def extract_payload(scripts):
    if isinstance(scripts, str):
        scripts = [scripts]

    if not isinstance(scripts, list) or not scripts:
        return _fail("extract_payload: invalid script")

    chunks = enqueue_chunks(scripts)

    if not chunks:
        return _fail("extract_payload: enqueue payload not found")

    candidates = [data for data in (parse_chunk(chunk) for chunk in chunks) if data]

    # Long conversations can be split across several enqueue calls, so fall back
    # to reading them as one concatenated payload.
    if not candidates:
        joined = parse_chunk("".join(chunks))

        if joined:
            candidates = [joined]

    if not candidates:
        return _fail("extract_payload: payload JSON parse failed")

    return _ok(candidates)



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



def normalize_file_id(value):
    if not isinstance(value, str) or not value:
        return None

    value = value.split("?")[0]

    for prefix in ("sediment://", "file-service://"):
        if value.startswith(prefix):
            value = value[len(prefix):]

    value = value.rstrip("/")

    if value.endswith("/raw"):
        value = value[:-4]

    value = value.split("/")[-1]

    for prefix in ("file_", "file-"):
        if value.startswith(prefix):
            value = value[len(prefix):]

    value = value.replace("-", "").lower()

    return value or None


def walk_mapping(mapping):
    root_id = None

    for node_id, node in mapping.items():
        if isinstance(node, dict) and node.get("parent") is None:
            root_id = node_id
            break

    if root_id is None:
        nodes = [n for n in mapping.values() if isinstance(n, dict)]
        return sorted(
            nodes,
            key=lambda n: ((n.get("message") or {}).get("create_time") or 0)
        )

    ordered = []
    seen = set()
    current = root_id

    while current and current not in seen:
        seen.add(current)
        node = mapping.get(current)

        if not isinstance(node, dict):
            break

        ordered.append(node)

        children = node.get("children") or []

        if not children:
            break

        current = children[-1]

    return ordered


def build_part(part):
    if not part:
        return None

    if isinstance(part, str):
        text = restore_utf8(part).strip()
        if not text:
            return None
        return {"type": "text", "text": text}

    if not isinstance(part, dict):
        return None

    part_type = ASSET_PART_TYPES.get(part.get("content_type"))

    if not part_type:
        return None

    pointer = part.get("asset_pointer")
    file_id = normalize_file_id(pointer)

    if not file_id:
        return None

    return assetlib.build_entry(
        entry_type=part_type,
        file_id=file_id,
        asset_pointer=pointer,
        mime_type=part.get("mime_type"),
        size_bytes=part.get("size_bytes"),
        width=part.get("width"),
        height=part.get("height"),
    )


def build_attachments(message):
    metadata = message.get("metadata") or {}
    attachments = metadata.get("attachments")

    if not isinstance(attachments, list):
        return []

    entries = []

    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue

        file_id = normalize_file_id(attachment.get("id"))

        if not file_id:
            continue

        mime_type = attachment.get("mime_type") or attachment.get("mimeType")
        name = restore_utf8(attachment.get("name") or "")

        entries.append(assetlib.build_entry(
            entry_type="image" if assetlib.is_embeddable(mime_type) else "file",
            file_id=file_id,
            asset_pointer=attachment.get("id"),
            name=name,
            mime_type=mime_type,
            size_bytes=attachment.get("size") or attachment.get("file_size"),
            origin="upload",
        ))

    return entries


def get_messages(mapping):
    if not isinstance(mapping, dict):
        return _fail("get_messages: mapping is not a dict")

    try:
        messages = []

        for node in walk_mapping(mapping):
            message = node.get("message")

            if not isinstance(message, dict):
                continue

            author = message.get("author") or {}
            role = author.get("role")
            content = message.get("content") or {}
            content_type = content.get("content_type")

            if content_type not in KEEP_CONTENT_TYPES:
                continue

            if role == "tool":
                if content_type != "multimodal_text":
                    continue
                role = "assistant"
            elif role not in ("user", "assistant"):
                continue

            content_block = []

            for attachment in build_attachments(message):
                content_block.append(attachment)

            parts = content.get("parts")

            if isinstance(parts, list):
                for part in parts:
                    entry = build_part(part)
                    if entry:
                        content_block.append(entry)

            if not content_block:
                continue

            metadata = message.get("metadata") or {}
            title = metadata.get("image_gen_title")

            if title:
                for entry in content_block:
                    if entry["type"] != "text" and not entry.get("title"):
                        entry["title"] = restore_utf8(title)

            messages.append({
                "id": message.get("id"),
                "role": role,
                "content": content_block,
                "timestamp": message.get("create_time")
            })

        if not messages:
            return _fail("get_messages: no messages extracted")

        return _ok(messages)
    except Exception as e:
        return _fail(f"get_messages: failed: {e}")


def collect_assets(messages):
    return assetlib.collect(messages)


def downloadable(wanted):
    return {
        file_id: entries
        for file_id, entries in wanted.items()
        if entries[0].get("embeddable")
    }


def fetch_assets(url, wanted):
    if not wanted:
        return _ok({})

    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    downloaded = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            try:
                page = browser.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                except PlaywrightTimeoutError:
                    pass

                try:
                    page.wait_for_selector("img", timeout=10000)
                except PlaywrightTimeoutError:
                    return _fail("fetch_assets: no images rendered on the page")

                for _ in range(10):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(250)

                found = page.eval_on_selector_all(
                    "img[src], source[srcset], a[href]",
                    """els => els.map(el => ({
                        src: el.currentSrc || el.src || el.href || '',
                        alt: el.getAttribute('alt') || ''
                    }))"""
                )

                index = {}

                for item in found:
                    file_id = normalize_file_id(item.get("src"))

                    if file_id and file_id in wanted and file_id not in index:
                        index[file_id] = item

                for file_id, item in index.items():
                    try:
                        response = page.request.get(item["src"], timeout=30000)

                        if not response.ok:
                            continue

                        mime_type = assetlib.normalize_mime(response.headers.get("content-type"))
                        declared = response.headers.get("content-length")

                        if declared and declared.isdigit():
                            if int(declared) > assetlib.MAX_EMBED_BYTES:
                                continue

                        body = response.body()

                        if not assetlib.should_download(mime_type, len(body)):
                            continue

                        downloaded[file_id] = {
                            "data": body,
                            "mime_type": mime_type,
                            "url": item["src"],
                            "alt": restore_utf8(item.get("alt") or ""),
                        }
                    except Exception:
                        continue
            finally:
                browser.close()

    except Exception as e:
        return _fail(f"fetch_assets: failed: {e}")

    return _ok(downloaded)


def save_assets(wanted, downloaded, conversation_id):
    target_dir = assets_dir / str(conversation_id)

    for file_id, entries in wanted.items():
        asset = downloaded.get(file_id)

        if not asset:
            assetlib.mark_unavailable(entries)
            continue

        mime_type = asset.get("mime_type") or entries[0].get("mime_type")

        try:
            file_path = assetlib.save_binary(
                target_dir,
                file_id,
                asset["data"],
                mime_type,
                entries[0].get("name"),
            )
        except Exception:
            assetlib.mark_unavailable(entries)
            continue

        assetlib.apply_download(
            entries,
            file_path,
            app_dir,
            mime_type=mime_type,
            url=asset.get("url"),
            alt=asset.get("alt"),
            size_bytes=len(asset["data"]),
        )

    return assetlib.summarize(wanted)


def load_chatgpt_chat(url):

    html_res = html_fetcher(url)
    if not html_res.get("ok"):
        return {"ok": False, "message": html_res.get("message", "html_fetcher failed")}
    html = html_res["value"]

    script_res = script_parser(html)
    if not script_res.get("ok"):
        return {"ok": False, "message": script_res.get("message", "script_parser failed")}
    scripts = script_res["value"]

    payload_res = extract_payload(scripts)
    if not payload_res.get("ok"):
        return {"ok": False, "message": payload_res.get("message", "extract_payload failed")}

    # Only one of the enqueue chunks carries the conversation; the others are
    # routing or streaming noise, so take the first that decodes into one.
    conv_res = None

    for payload_data in payload_res["value"]:
        decoded_res = decode(payload_data)

        if not decoded_res.get("ok"):
            continue

        attempt = get_conversation_data(decoded_res["value"])

        if attempt.get("ok"):
            conv_res = attempt
            break

        conv_res = conv_res or attempt

    if not conv_res or not conv_res.get("ok"):
        return {
            "ok": False,
            "message": (conv_res or {}).get("message", "get_conversation_data failed"),
        }

    conversation_id, title, mapping = conv_res["value"]

    messages_res = get_messages(mapping)
    if not messages_res.get("ok"):
        return {"ok": False, "message": messages_res.get("message", "get_messages failed")}
    messages = messages_res["value"]

    wanted = collect_assets(messages)
    fetchable = downloadable(wanted)
    assets_saved = 0
    assets_skipped = len(wanted)

    if fetchable:
        assets_res = fetch_assets(url, fetchable)

        if assets_res.get("ok"):
            assets_saved, assets_skipped = save_assets(wanted, assets_res["value"], conversation_id)
        else:
            assetlib.mark_unavailable([e for entries in fetchable.values() for e in entries])
            assets_saved, assets_skipped = assetlib.summarize(wanted)

    result = {
        "conversation_id":conversation_id,
        "platform":"chatgpt",
        "source_url":url,
        "title":title,
        "scraped_at":datetime.now(timezone.utc).isoformat(),
        "has_assets": bool(wanted),
        "assets_saved": assets_saved,
        "assets_skipped": assets_skipped,
        "messages":messages
    }

    return {"data": result, "ok": True}
