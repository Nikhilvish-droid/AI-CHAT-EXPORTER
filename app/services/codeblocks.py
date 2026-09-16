import re


FENCE_PATTERN = re.compile(r"```([A-Za-z0-9_+.-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)
OPEN_FENCE_PATTERN = re.compile(r"```([A-Za-z0-9_+.-]*)[ \t]*\r?\n(.*)\Z", re.DOTALL)

BOX_DRAWING = set("┌┐└┘│─├┤┬┴┼╔╗╚╝║═╠╣╦╩╬▲▼◄►↓↑←→")

ASCII_ART_PATTERN = re.compile(r"[+|]-{2,}|-{2,}[+|]|\+={2,}|={2,}\+")

TABLE_ROW_PATTERN = re.compile(r"^\|.*\|$")

MIN_ART_LINES = 2


def normalize_newlines(text):
    if not isinstance(text, str):
        return ""

    if "\n" in text or "\r" in text:
        return text.replace("\r\n", "\n")

    if "\\n" in text:
        return text.replace("\\r\\n", "\n").replace("\\n", "\n")

    return text


def fingerprint(text):
    return "\n".join(line.rstrip() for line in text.strip().split("\n"))


def is_art_line(line):
    stripped = line.strip()

    if not stripped:
        return False

    if sum(1 for ch in stripped if ch in BOX_DRAWING) >= 3:
        return True

    if TABLE_ROW_PATTERN.match(stripped) and stripped.count("|") >= 3:
        return False

    return bool(ASCII_ART_PATTERN.search(stripped))


def find_art_runs(text):
    runs = []
    block = []

    def flush():
        if not block:
            return

        art = sum(1 for line in block if is_art_line(line))

        if art >= MIN_ART_LINES and art >= len(block) * 0.3:
            runs.append("\n".join(block))

    for line in text.split("\n"):
        if line.strip():
            block.append(line)
            continue

        flush()
        block.clear()

    flush()

    return runs


def extract_from_text(text):
    text = normalize_newlines(text)
    found = []
    remainder = text

    for language, body in FENCE_PATTERN.findall(text):
        code = body.rstrip()

        if code.strip():
            found.append({"language": (language or "").strip().lower(), "code": code})

    remainder = FENCE_PATTERN.sub("\n", text)

    if remainder.count("```") % 2 == 1:
        match = OPEN_FENCE_PATTERN.search(remainder)

        if match:
            code = match.group(2).rstrip()

            if code.strip():
                found.append({"language": (match.group(1) or "").strip().lower(), "code": code})

            remainder = remainder[: match.start()]

    for run in find_art_runs(remainder):
        found.append({"language": "diagram", "code": run.rstrip()})

    return found


def extract_code_blocks(messages):
    blocks = []
    seen = set()

    for message in messages or []:
        role = message.get("role")

        for entry in message.get("content") or []:
            if entry.get("type") != "text":
                continue

            for found in extract_from_text(entry.get("text") or ""):
                key = fingerprint(found["code"])

                if not key or key in seen:
                    continue

                seen.add(key)

                language = found["language"]
                is_diagram = language == "diagram" or any(
                    is_art_line(line) for line in found["code"].split("\n")
                )

                blocks.append({
                    "language": language or "text",
                    "code": found["code"],
                    "role": role,
                    "kind": "diagram" if is_diagram else "code",
                    "lines": len(found["code"].split("\n")),
                    "chars": len(found["code"]),
                })

    return blocks
