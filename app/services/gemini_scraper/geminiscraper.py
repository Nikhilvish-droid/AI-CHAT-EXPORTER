from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
import uuid
import time


app_dir = Path(__file__).parent.parent.parent
folder = "1"

html_file = app_dir / "demo_data" / "gemini" / folder / "scrape.html"
chat = app_dir / "demo_data" / "gemini" / folder / "chat.json"


def _ok(value):
    return {"ok": True, "value": value}


def _fail(message: str):
    return {"ok": False, "message": message}


def get_html(url):
    if not isinstance(url, str) or not url.strip():
        return _fail("get_html: invalid url")

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
                        "get_html: conversation content not found. "
                        "The share page may still be loading, require sign-in, "
                        "or use an unsupported Gemini share format."
                    )

                try:
                    render_html = page.inner_html("main")
                except Exception:
                    render_html = page.content()
            finally:
                browser.close()

    except Exception as e:
        return _fail(f"get_html: request failed: {e}")

    if not isinstance(render_html, str) or not render_html.strip():
        return _fail("get_html: empty html returned")

    try:
        html_file.parent.mkdir(parents=True, exist_ok=True)

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(render_html)

    except Exception as e:
        return _fail(f"get_html: could not write html file: {e}")

    return _ok(render_html)


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


def _extract_model_text(md_container) -> str:
    for tag in md_container.find_all(
        ["button", "gem-icon-button", "elicitations", "table-footer"]
    ):
        tag.decompose()

    for table in md_container.find_all("table"):
        formatted = _format_table(table)
        table.replace_with(f"\n{formatted}\n" if formatted else "")

    return md_container.get_text(separator="\n", strip=True)


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
        text = (turn.get("text") or "").strip()
        role = turn.get("role")
        if role not in ["user", "assistant"] or not text:
            continue
        normalized_messages.append({
            "id": str(uuid.uuid4()),
            "role": role,
            "content": [{"type": "text", "text": text}],
            "timestamp": round(current_epoch + idx, 6),
        })

    if not normalized_messages:
        return _fail("json_schema: no valid messages after normalizing turns")

    chat_json = {
        "conversation_id": conversation_id,
        "platform": platform,
        "source_url": source_url,
        "title": title,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "messages": normalized_messages,
    }

    try:
        chat.parent.mkdir(parents=True, exist_ok=True)
        with open(chat, "w", encoding="utf-8") as f:
            json.dump(chat_json, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return _fail(f"json_schema: could not write chat file: {e}")

    return _ok(chat_json)


def parse_chat(html, url):
    if not isinstance(html, str) or not html.strip():
        return _fail("parse_chat: invalid html_data")
    if not isinstance(url, str) or not url.strip():
        return _fail("parse_chat: invalid url")

    try:
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("h1", class_="headline")
        title = (
            title_tag.get_text(strip=True) if title_tag else "Gemini Conversation"
        )

        turns = []
        share_viewers = soup.find_all("share-turn-viewer")
        if not share_viewers:
            return _fail(
                "parse_chat: share-turn-viewer not found. "
                "This Gemini share format is not supported."
            )

        for turn_viewer in share_viewers:
            user_elem = turn_viewer.find("user-query")
            if user_elem:
                user_text = _extract_user_text(user_elem)
                if user_text:
                    turns.append({"role": "user", "text": user_text})

            model_elem = turn_viewer.find("message-content")
            if model_elem:
                md_container = model_elem.find("div", class_="markdown")
                if md_container:
                    model_text = _extract_model_text(md_container)
                    if model_text:
                        turns.append({"role": "assistant", "text": model_text})

        if not turns:
            return _fail("parse_chat: no user or assistant messages found")

        return json_schema(
            platform="gemini",
            source_url=url,
            title=title,
            raw_turns=turns,
        )
    except Exception as e:
        return _fail(f"parse_chat: failed to parse html: {e}")


def load_gemini_chat(url):
    html_res = get_html(url)
    if not html_res.get("ok"):
        return {"ok": False, "message": html_res.get("message", "get_html failed")}
    html_data = html_res["value"]

    chat_res = parse_chat(html_data, url)
    if not chat_res.get("ok"):
        return {"ok": False, "message": chat_res.get("message", "parse_chat failed")}
    chat_data = chat_res["value"]

    print(len(chat_data.get("messages", [])), "messages loaded")

    return {"ok": True, "data": chat_data}
