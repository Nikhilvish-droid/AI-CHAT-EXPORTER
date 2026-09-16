import json
import hashlib
from curl_cffi import requests as cffi_request
from datetime import datetime, timezone
import time
from pathlib import Path

from backend.app.services import assets as assetlib


folder = "nontext-2"
app_dir = Path(__file__).parent.parent.parent
platform = "claude"

chat_data = app_dir/"demo_data"/platform/folder/"chat_data.json"
scrape_data = app_dir/"demo_data"/platform/folder/"fetch_data.json"
assets_dir = app_dir/"demo_data"/platform/folder/"assets"

WIDGET_TOOLS = {"visualize:show_widget"}

SVG_MIME = "image/svg+xml"


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def content_id(value):
    if isinstance(value, str):
        value = value.encode("utf-8")

    return hashlib.sha1(value).hexdigest()[:32]


def fetch_data(url):

    share_id = url.split('/')[-1]
    api_url = f"https://claude.ai/api/chat_snapshots/{share_id}?rendering_mode=messages&render_all_tools=true"

    try:
        response = cffi_request.get(api_url, impersonate="chrome124", timeout=15)

        if response.status_code == 200:
            parsed_json = response.json()

            scrape_data.parent.mkdir(parents=True, exist_ok=True)

            with open(scrape_data, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=4, ensure_ascii=False)

            return _ok(parsed_json)
        else:
            return _fail(f"Could not scrape data, status code: {response.status_code}")

    except Exception as e:
        return _fail(f"Request failed: {str(e)}")


def widget_entry(block):
    payload = block.get("input")

    if not isinstance(payload, dict):
        return None

    code = payload.get("widget_code")

    if not isinstance(code, str) or not code.strip():
        return None

    stripped = code.lstrip()
    is_svg = stripped.startswith("<svg")
    data = code.encode("utf-8")

    entry = assetlib.build_entry(
        entry_type="image" if is_svg else "file",
        file_id=content_id(data),
        asset_pointer=f"widget://{block.get('id') or ''}",
        mime_type=SVG_MIME if is_svg else "text/html",
        size_bytes=len(data),
        name=payload.get("title"),
        title=payload.get("title"),
    )

    entry["inline"] = code if is_svg else None

    return entry


def gallery_entries(block):
    entries = []

    for inner in block.get("content") or []:
        if not isinstance(inner, dict):
            continue

        if inner.get("type") != "image_gallery":
            continue

        for image in inner.get("images") or []:
            if not isinstance(image, dict):
                continue

            url = image.get("url")
            file_id = assetlib.hash_id(url)

            if not file_id:
                continue

            entries.append(assetlib.build_entry(
                entry_type="image",
                file_id=file_id,
                asset_pointer=url,
                mime_type=assetlib.mime_from_name(url, "image/jpeg"),
                name=image.get("title"),
                title=image.get("title"),
                alt=image.get("title"),
                url=url,
                width=image.get("width"),
                height=image.get("height"),
            ))

    return entries


def local_resource_entries(block):
    entries = []

    for inner in block.get("content") or []:
        if not isinstance(inner, dict):
            continue

        if inner.get("type") != "local_resource":
            continue

        mime_type = inner.get("mime_type")
        file_id = inner.get("uuid") or content_id(inner.get("file_path") or "")

        entry = assetlib.build_entry(
            entry_type="image" if assetlib.is_embeddable(mime_type) else "file",
            file_id=str(file_id).replace("-", "")[:32],
            asset_pointer=inner.get("file_path"),
            mime_type=mime_type,
            name=inner.get("name"),
            title=inner.get("name"),
            origin="generated",
        )

        entry["missing"] = True

        if not entry.get("skip_reason"):
            entry["skip_reason"] = assetlib.SKIP_UNAVAILABLE

        entries.append(entry)

    return entries


def upload_placeholders(message):
    declared = (message.get("file_count") or 0) + (message.get("image_count") or 0)

    if declared < 1:
        return []

    entries = []

    for index in range(declared):
        entry = assetlib.build_entry(
            entry_type="file",
            file_id=content_id(f"{message.get('uuid')}:upload:{index}"),
            asset_pointer=None,
            mime_type=None,
            origin="upload",
        )

        entry["missing"] = True
        entry["skip_reason"] = assetlib.SKIP_UNAVAILABLE
        entries.append(entry)

    return entries


def attachment_entries(message):
    entries = []

    for key in ("attachments", "files"):
        for attachment in message.get(key) or []:
            if not isinstance(attachment, dict):
                continue

            name = (
                attachment.get("file_name")
                or attachment.get("name")
                or attachment.get("document_name")
            )

            mime_type = (
                attachment.get("file_type")
                or attachment.get("mime_type")
                or assetlib.mime_from_name(name)
            )

            raw_id = attachment.get("id") or attachment.get("file_uuid") or name

            if not raw_id:
                continue

            entry = assetlib.build_entry(
                entry_type="image" if assetlib.is_embeddable(mime_type) else "file",
                file_id=content_id(str(raw_id)),
                asset_pointer=attachment.get("file_url") or attachment.get("id"),
                mime_type=mime_type,
                size_bytes=attachment.get("file_size") or attachment.get("size"),
                name=name,
                title=name,
                url=attachment.get("file_url"),
                origin="upload",
            )

            entry["missing"] = True

            if not entry.get("skip_reason"):
                entry["skip_reason"] = assetlib.SKIP_UNAVAILABLE

            entries.append(entry)

    return entries


def get_chat_messages(data):
    messages = []

    for message in data.get("chat_messages") or []:
        if not isinstance(message, dict):
            continue

        role = message.get("sender")

        if role == "human":
            role = "user"

        if role not in ("user", "assistant"):
            continue

        content_block = []

        declared = attachment_entries(message)

        if not declared:
            declared = upload_placeholders(message)

        for entry in declared:
            content_block.append(entry)

        for block in message.get("content") or []:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            if block_type == "text":
                text = (block.get("text") or "").strip()

                if text:
                    content_block.append({"type": "text", "text": text})

            elif block_type == "tool_use":
                if block.get("name") in WIDGET_TOOLS:
                    entry = widget_entry(block)

                    if entry:
                        content_block.append(entry)

            elif block_type == "tool_result":
                for entry in gallery_entries(block):
                    content_block.append(entry)

                for entry in local_resource_entries(block):
                    content_block.append(entry)

        if not content_block:
            continue

        timestamp = message.get("created_at")

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                timestamp = time.time()

        messages.append({
            "id": message.get("uuid"),
            "role": role,
            "content": content_block,
            "timestamp": timestamp,
        })

    return messages


def save_inline_assets(wanted, conversation_id):
    target_dir = assets_dir / str(conversation_id)

    for file_id, entries in wanted.items():
        inline = entries[0].get("inline")

        if not inline:
            continue

        try:
            file_path = assetlib.save_binary(
                target_dir,
                file_id,
                inline.encode("utf-8"),
                entries[0].get("mime_type"),
            )
        except Exception:
            assetlib.mark_unavailable(entries)
            continue

        assetlib.apply_download(
            entries,
            file_path,
            app_dir,
            mime_type=entries[0].get("mime_type"),
            size_bytes=len(inline.encode("utf-8")),
        )


def download_remote_assets(wanted, conversation_id):
    target_dir = assets_dir / str(conversation_id)

    for file_id, entries in wanted.items():
        entry = entries[0]

        if entry.get("path") or entry.get("inline"):
            continue

        if not entry.get("embeddable"):
            continue

        url = entry.get("url")

        if not url:
            assetlib.mark_unavailable(entries)
            continue

        try:
            response = cffi_request.get(url, impersonate="chrome124", timeout=20)

            if response.status_code != 200:
                assetlib.mark_unavailable(entries)
                continue

            mime_type = assetlib.normalize_mime(
                response.headers.get("content-type")
            ) or entry.get("mime_type")

            body = response.content

            if not assetlib.should_download(mime_type, len(body)):
                assetlib.mark_unavailable(entries)
                continue

            file_path = assetlib.save_binary(
                target_dir,
                file_id,
                body,
                mime_type,
            )
        except Exception:
            assetlib.mark_unavailable(entries)
            continue

        assetlib.apply_download(
            entries,
            file_path,
            app_dir,
            mime_type=mime_type,
            url=url,
            size_bytes=len(body),
        )


def strip_inline(messages):
    for message in messages:
        for entry in message.get("content", []):
            if "inline" in entry:
                entry.pop("inline")


def convert_data_to_scheme(data, url, messages, assets_saved, assets_skipped, has_assets):

    json_schema = {
        "conversation_id": data.get("conversation_uuid"),
        "platform": "claude",
        "source_url": url,
        "title": data.get("snapshot_name"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "has_assets": has_assets,
        "assets_saved": assets_saved,
        "assets_skipped": assets_skipped,
        "messages": messages,
    }

    chat_data.parent.mkdir(parents=True, exist_ok=True)

    with open(chat_data, 'w', encoding="utf-8") as f:
        json.dump(json_schema, f, indent=4, ensure_ascii=False)

    return json_schema


def load_claude_chat(url):

    chat_response = fetch_data(url)

    if not chat_response.get("ok"):
        return {"ok": False, "message": chat_response.get("message", "fetch_data failed")}

    data = chat_response.get("value")

    messages = get_chat_messages(data)

    if not messages:
        return {"ok": False, "message": "get_chat_messages: no messages extracted"}

    conversation_id = data.get("conversation_uuid")

    wanted = assetlib.collect(messages)

    if wanted:
        save_inline_assets(wanted, conversation_id)
        download_remote_assets(wanted, conversation_id)

    assets_saved, assets_skipped = assetlib.summarize(wanted)

    strip_inline(messages)

    formatted_data = convert_data_to_scheme(
        data,
        url,
        messages,
        assets_saved,
        assets_skipped,
        bool(wanted),
    )

    return {"ok": True, "data": formatted_data}


if __name__ == "__main__":

    share_url = "https://claude.ai/share/087cf7b8-a6bd-4a6f-98a7-bba5a332c58f"
    print(load_claude_chat(share_url))
