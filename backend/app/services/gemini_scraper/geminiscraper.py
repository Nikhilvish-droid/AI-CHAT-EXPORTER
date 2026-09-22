from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import uuid
import time
import hashlib


from app.services import assets as assetlib

app_dir = Path(__file__).parent.parent.parent
platform = "gemini"

assets_dir = app_dir / "storage" / "assets" / platform

TURN_SELECTOR = "share-turn-viewer"

CODE_BLOCK_SELECTORS = ("code-block", "ms-code-block", "pre")

LANGUAGE_PATTERN = re.compile(r"[^a-z0-9+#._-]")

ASSET_SELECTOR = (
    "share-turn-viewer img[src], "
    "share-turn-viewer source[srcset], "
    "share-turn-viewer a[download][href]"
)


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def asset_id_for(src):
    if not isinstance(src, str) or not src.strip():
        return None

    if src.startswith("data:"):
        return None

    base = src.split("?")[0].split("#")[0].strip()

    if not base:
        return None

    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:32]


def capture_page(url):
    if not isinstance(url, str) or not url.strip():
        return _fail("capture_page: invalid url")

    render_html = None
    assets = {}

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
                    page.wait_for_selector(
                        "message-content, share-turn-viewer",
                        timeout=10000,
                    )
                except PlaywrightTimeoutError:
                    return _fail(
                        "capture_page: conversation content not found. "
                        "The share page may still be loading, require sign-in, "
                        "or use an unsupported Gemini share format."
                    )

                for _ in range(10):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(250)

                try:
                    render_html = page.inner_html("main")
                except Exception:
                    render_html = page.content()

                try:
                    found = page.eval_on_selector_all(
                        ASSET_SELECTOR,
                        """els => els.map(el => ({
                            src: el.getAttribute('src') || el.getAttribute('href') || '',
                            current: el.currentSrc || '',
                            alt: el.getAttribute('alt') || '',
                            width: el.naturalWidth || 0,
                            height: el.naturalHeight || 0
                        }))"""
                    )
                except Exception:
                    found = []

                for item in found:
                    candidates = [item.get("src"), item.get("current")]
                    target = next((c for c in candidates if c and not c.startswith("data:")), None)

                    if not target:
                        continue

                    ids = [asset_id_for(c) for c in candidates if c]
                    ids = [i for i in ids if i]

                    if not ids or all(i in assets for i in ids):
                        continue

                    try:
                        response = page.request.get(target, timeout=30000)

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

                        payload = {
                            "data": body,
                            "mime_type": mime_type,
                            "url": target,
                            "alt": item.get("alt") or "",
                            "width": item.get("width") or 0,
                            "height": item.get("height") or 0,
                        }
                    except Exception:
                        continue

                    for asset_id in ids:
                        assets[asset_id] = payload
            finally:
                browser.close()

    except Exception as e:
        return _fail(f"capture_page: request failed: {e}")

    if not isinstance(render_html, str) or not render_html.strip():
        return _fail("capture_page: empty html returned")

    return _ok({"html": render_html, "assets": assets})


def _format_table(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [
            cell.get_text(separator=" ", strip=True)
            for cell in tr.find_all(["th", "td"])
        ]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _extract_user_text(user_elem) -> str:
    lines = user_elem.find_all("p", class_="query-text-line")
    texts = [
        line.get_text(separator=" ", strip=True)
        for line in lines
        if line.get_text(strip=True)
    ]
    if texts:
        return "\n".join(texts)

    query_text = user_elem.find("div", class_="query-text")
    target = query_text if query_text else user_elem
    for hidden in target.find_all(class_=["cdk-visually-hidden", "screen-reader-user-query-label"]):
        hidden.decompose()
    return target.get_text(separator="\n", strip=True)


def _code_language(node) -> str:
    """Best-effort language label for a Gemini code block."""

    candidates = []

    code_elem = node.find("code") if node.name != "code" else node

    for elem in (node, code_elem):
        if elem is None:
            continue

        candidates.append(elem.get("data-language") or elem.get("language") or "")

        for css_class in elem.get("class") or []:
            if css_class.startswith("language-"):
                candidates.append(css_class[len("language-"):])

    header = node.find(
        ["div", "span"],
        class_=lambda value: bool(value) and "code-block-decoration" in " ".join(
            value if isinstance(value, list) else [value]
        ),
    )

    if header is not None:
        candidates.append(header.get_text(strip=True))

    for candidate in candidates:
        language = LANGUAGE_PATTERN.sub("", str(candidate).strip().lower())

        if language and language != "code":
            return language

    return ""


def _replace_code_blocks(container):
    """Turn rendered code blocks back into fenced markdown.

    Gemini renders code as a tree of highlighted spans. Reading it with
    get_text(separator="\\n") would put every token on its own line and lose the
    language, so the downstream code-block extractor would never see it. Fencing
    the block here keeps it intact and verbatim in the exported PDF.
    """

    for selector in CODE_BLOCK_SELECTORS:
        for node in container.find_all(selector):
            # A <pre> nested inside an already handled <code-block> is gone by now.
            if node.parent is None:
                continue

            code_elem = node.find("code") or node
            code = code_elem.get_text()

            if not code.strip():
                node.decompose()
                continue

            language = _code_language(node)
            fenced = "\n```%s\n%s\n```\n" % (language, code.strip("\n").rstrip())

            node.replace_with(fenced)


def _extract_model_text(md_container) -> str:
    for tag in md_container.find_all(
        ["button", "gem-icon-button", "elicitations", "table-footer"]
    ):
        tag.decompose()

    _replace_code_blocks(md_container)

    for table in md_container.find_all("table"):
        formatted = _format_table(table)
        table.replace_with(f"\n{formatted}\n" if formatted else "")

    return md_container.get_text(separator="\n", strip=True)


def extract_assets(element, assets, origin="generated"):
    if element is None:
        return []

    entries = []
    seen = set()

    for node in element.find_all(["img", "source", "a"]):
        src = node.get("src") or node.get("srcset") or node.get("href")

        if not src:
            continue

        src = src.split(",")[0].strip().split(" ")[0]
        asset_id = asset_id_for(src)

        if not asset_id or asset_id in seen:
            continue

        seen.add(asset_id)
        asset = assets.get(asset_id)

        if node.name == "a" and not asset:
            continue

        alt = node.get("alt") or (asset or {}).get("alt") or ""
        mime_type = (asset or {}).get("mime_type") or assetlib.mime_from_name(src)

        entry = assetlib.build_entry(
            entry_type="image" if node.name in ("img", "source") else "file",
            file_id=asset_id,
            asset_pointer=src,
            mime_type=mime_type,
            size_bytes=len(asset["data"]) if asset else None,
            alt=alt,
            title=alt,
            url=(asset or {}).get("url") or src,
            width=(asset or {}).get("width") or node.get("width"),
            height=(asset or {}).get("height") or node.get("height"),
            origin=origin,
        )

        if asset:
            entry["embeddable"] = True
            entry["skip_reason"] = None

        entries.append(entry)

    return entries


def collect_assets(messages):
    return assetlib.collect(messages)


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


def json_schema(
        platform: str,
        source_url: str,
        title: str,
        raw_turns: list,
        conversation_id: str = None,
        ):
    if not raw_turns:
        return _fail("json_schema: no conversation turns to save")

    if not conversation_id:
        url_id_match = re.search(r"([a-f0-9\-]{16,36}|[a-zA-Z0-9_\-]{8,})/?$", source_url)
        conversation_id = url_id_match.group(1) if url_id_match else str(uuid.uuid4())

    normalized_messages = []
    current_epoch = time.time()

    for idx, turn in enumerate(raw_turns):
        role = turn.get("role")

        if role not in ["user", "assistant"]:
            continue

        content_block = []

        text = (turn.get("text") or "").strip()

        if text:
            content_block.append({"type": "text", "text": text})

        for entry in turn.get("assets") or []:
            content_block.append(entry)

        if not content_block:
            continue

        normalized_messages.append({
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content_block,
            "timestamp": round(current_epoch + idx, 6),
        })

    if not normalized_messages:
        return _fail("json_schema: no valid messages after normalizing turns")

    return _ok((conversation_id, normalized_messages))


def parse_chat(html, url, assets=None):
    if not isinstance(html, str) or not html.strip():
        return _fail("parse_chat: invalid html_data")
    if not isinstance(url, str) or not url.strip():
        return _fail("parse_chat: invalid url")

    assets = assets or {}

    try:
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("h1", class_="headline")
        title = (
            title_tag.get_text(strip=True) if title_tag else "Gemini Conversation"
        )

        turns = []
        share_viewers = soup.find_all(TURN_SELECTOR)

        if not share_viewers:
            return _fail(
                "parse_chat: share-turn-viewer not found. "
                "This Gemini share format is not supported."
            )

        for turn_viewer in share_viewers:
            user_elem = turn_viewer.find("user-query")

            if user_elem:
                user_assets = extract_assets(user_elem, assets, origin="upload")
                user_text = _extract_user_text(user_elem)

                if user_text or user_assets:
                    turns.append({
                        "role": "user",
                        "text": user_text,
                        "assets": user_assets,
                    })

            model_elem = turn_viewer.find("message-content")

            if model_elem:
                model_assets = extract_assets(model_elem, assets)
                md_container = model_elem.find("div", class_="markdown")
                model_text = _extract_model_text(md_container) if md_container else ""

                if model_text or model_assets:
                    turns.append({
                        "role": "assistant",
                        "text": model_text,
                        "assets": model_assets,
                    })

        if not turns:
            return _fail("parse_chat: no user or assistant messages found")

        schema_res = json_schema(
            platform=platform,
            source_url=url,
            title=title,
            raw_turns=turns,
        )

        if not schema_res.get("ok"):
            return schema_res

        conversation_id, messages = schema_res["value"]

        return _ok((conversation_id, title, messages))

    except Exception as e:
        return _fail(f"parse_chat: failed to parse html: {e}")


def load_gemini_chat(url):
    capture_res = capture_page(url)

    if not capture_res.get("ok"):
        return {"ok": False, "message": capture_res.get("message", "capture_page failed")}

    html_data = capture_res["value"]["html"]
    downloaded = capture_res["value"]["assets"]

    chat_res = parse_chat(html_data, url, downloaded)

    if not chat_res.get("ok"):
        return {"ok": False, "message": chat_res.get("message", "parse_chat failed")}

    conversation_id, title, messages = chat_res["value"]

    wanted = collect_assets(messages)
    assets_saved = 0
    assets_skipped = len(wanted)

    if wanted:
        assets_saved, assets_skipped = save_assets(wanted, downloaded, conversation_id)

    result = {
        "conversation_id": conversation_id,
        "platform": "gemini",
        "source_url": url,
        "title": title,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "has_assets": bool(wanted),
        "assets_saved": assets_saved,
        "assets_skipped": assets_skipped,
        "messages": messages,
    }

    return {"ok": True, "data": result}



if __name__ == "__main__":
    url="https://share.gemini.google/BbVnukg1YMHC"
    load_gemini_chat(url)