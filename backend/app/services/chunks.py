import re


MAX_CHARS = 1000
OVERLAP = 100


def clean_embedtext(text: str):
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


def message_text(message):
    parts = []

    for entry in message.get("content", []):
        if entry.get("type") != "text":
            continue

        text = entry.get("text")

        if text:
            parts.append(text)

    return "\n".join(parts).strip()


def group_turns(messages):
    turns = []
    index = 0

    while index < len(messages):
        message = messages[index]
        role = message.get("role")
        texts = [message_text(message)]
        ids = [message.get("id")]
        index += 1

        while index < len(messages) and messages[index].get("role") == role:
            texts.append(message_text(messages[index]))
            ids.append(messages[index].get("id"))
            index += 1

        turns.append({
            "role": role,
            "text": "\n\n".join(t for t in texts if t).strip(),
            "ids": [i for i in ids if i],
        })

    return turns


def pair_turns(turns):
    pairs = []
    index = 0

    while index < len(turns):
        current = turns[index]
        following = turns[index + 1] if index + 1 < len(turns) else None

        if current["role"] == "user" and following and following["role"] == "assistant":
            pairs.append({
                "text": f" User: {current['text']} \n\n assistant: {following['text']} ",
                "ids": current["ids"] + following["ids"],
                "roles": ["user", "assistant"],
                "has_text": bool(current["text"] or following["text"]),
            })

            index += 2
            continue

        label = "User" if current["role"] == "user" else "assistant"

        pairs.append({
            "text": f" {label}: {current['text']} ",
            "ids": current["ids"],
            "roles": [current["role"]],
            "has_text": bool(current["text"]),
        })

        index += 1

    return [pair for pair in pairs if pair["has_text"]]


def build_chunk(chunks, conversation_id, text, ids, roles):
    chunks.append({
        "chunk_id": f"chunk-{len(chunks) + 1:03d}",
        "conversation_id": conversation_id,
        "type": "text",
        "text": text,
        "embedded_text": clean_embedtext(text),
        "verbatim": False,
        "source_message_ids": ids,
        "roles_included": roles,
        "order_index": len(chunks),
        "char_count": len(text),
    })


def create_chunks(data):
    if not isinstance(data, dict):
        return {"ok": False, "message": "create_chunks: data is not a dict", "chunks": []}

    messages = data.get("messages")

    if not isinstance(messages, list) or not messages:
        return {"ok": False, "message": "create_chunks: conversation has no messages", "chunks": []}

    conversation_id = data.get("conversation_id")
    chunks = []

    for pair in pair_turns(group_turns(messages)):
        text = pair["text"]

        if len(text) <= MAX_CHARS:
            build_chunk(chunks, conversation_id, text, pair["ids"], pair["roles"])
            continue

        step = max(1, MAX_CHARS - OVERLAP)

        for start in range(0, len(text), step):
            piece = text[start:start + MAX_CHARS]

            if not piece.strip():
                continue

            roles = pair["roles"] if start == 0 else ["assistant"]

            build_chunk(chunks, conversation_id, piece, pair["ids"], roles)

    if not chunks:
        return {
            "ok": False,
            "message": "create_chunks: conversation contained no text to summarise",
            "chunks": [],
        }

    covered = {i for chunk in chunks for i in chunk["source_message_ids"]}
    expected = {m.get("id") for m in messages if message_text(m)}

    return {
        "ok": True,
        "message": "chunks created successfully",
        "chunks": chunks,
        "messages_without_chunk": sorted(i for i in expected - covered if i),
    }
