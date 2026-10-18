import hashlib
import mimetypes
from pathlib import Path


MAX_EMBED_BYTES = 5 * 1024 * 1024

RASTER_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
    "image/bmp",
}

VECTOR_IMAGE_MIMES = {
    "image/svg+xml",
}

EMBEDDABLE_MIMES = RASTER_IMAGE_MIMES | VECTOR_IMAGE_MIMES

MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/csv": ".csv",
}

SKIP_NOT_EMBEDDABLE = "not_embeddable"
SKIP_TOO_LARGE = "too_large"
SKIP_UNAVAILABLE = "unavailable"


def normalize_mime(mime_type):
    if not isinstance(mime_type, str):
        return None

    mime_type = mime_type.split(";")[0].strip().lower()

    return mime_type or None


def extension_for(mime_type, fallback=".bin"):
    mime_type = normalize_mime(mime_type)

    if not mime_type:
        return fallback

    return MIME_EXTENSIONS.get(mime_type) or mimetypes.guess_extension(mime_type) or fallback


def mime_from_name(name, fallback=None):
    if not isinstance(name, str) or not name.strip():
        return fallback

    guessed, _ = mimetypes.guess_type(name)

    return normalize_mime(guessed) or fallback


def is_embeddable(mime_type):
    return normalize_mime(mime_type) in EMBEDDABLE_MIMES


def classify(mime_type, size_bytes=None):
    mime_type = normalize_mime(mime_type)

    if not mime_type:
        return False, SKIP_NOT_EMBEDDABLE

    if mime_type not in EMBEDDABLE_MIMES:
        return False, SKIP_NOT_EMBEDDABLE

    if isinstance(size_bytes, int) and size_bytes > MAX_EMBED_BYTES:
        return False, SKIP_TOO_LARGE

    return True, None


def should_download(mime_type, size_bytes=None):
    embeddable, _ = classify(mime_type, size_bytes)
    return embeddable


def hash_id(value):
    if not isinstance(value, str) or not value.strip():
        return None

    base = value.split("?")[0].split("#")[0].strip()

    if not base:
        return None

    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:32]


def build_entry(
    entry_type,
    file_id,
    asset_pointer=None,
    mime_type=None,
    size_bytes=None,
    name=None,
    title=None,
    alt=None,
    url=None,
    width=None,
    height=None,
    origin="generated",
):
    mime_type = normalize_mime(mime_type) or mime_from_name(name)
    embeddable, skip_reason = classify(mime_type, size_bytes)

    entry = {
        "type": entry_type,
        "file_id": file_id,
        "asset_pointer": asset_pointer,
        "origin": origin,
        "name": name or None,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "path": None,
        "url": url,
        "alt": alt or None,
        "title": title or None,
        "embeddable": embeddable,
        "skip_reason": skip_reason,
        "missing": not embeddable,
    }

    if width:
        entry["width"] = int(width)

    if height:
        entry["height"] = int(height)

    return entry


def collect(messages):
    wanted = {}

    for message in messages:
        for entry in message.get("content", []):
            if entry.get("type") == "text":
                continue

            file_id = entry.get("file_id")

            if file_id:
                wanted.setdefault(file_id, []).append(entry)

    return wanted


def mark_unavailable(entries):
    for entry in entries:
        entry["missing"] = True

        if not entry.get("skip_reason"):
            entry["skip_reason"] = SKIP_UNAVAILABLE


def save_binary(target_dir, file_id, data, mime_type, name=None):
    mime_type = normalize_mime(mime_type)
    extension = Path(name).suffix if name else ""

    if not extension:
        extension = extension_for(mime_type)

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{file_id}{extension}"

    with open(file_path, "wb") as handle:
        handle.write(data)

    return file_path


def apply_download(entries, file_path, app_dir, mime_type=None, url=None, alt=None, size_bytes=None):
    for entry in entries:
        entry["path"] = str(Path(file_path).relative_to(app_dir))
        entry["missing"] = False
        entry["skip_reason"] = None
        entry["embeddable"] = True

        if mime_type:
            entry["mime_type"] = normalize_mime(mime_type)

        if url:
            entry["url"] = url

        if size_bytes is not None:
            entry["size_bytes"] = size_bytes

        if alt and not entry.get("alt"):
            entry["alt"] = alt


def manifest(messages):
    seen = set()
    embedded = []
    missing = []

    for message in messages:
        for entry in message.get("content", []):
            if entry.get("type") == "text":
                continue

            file_id = entry.get("file_id")

            if file_id in seen:
                continue

            seen.add(file_id)

            if entry.get("path"):
                embedded.append(entry)
            else:
                missing.append(entry)

    return {"embedded": embedded, "missing": missing}


def reupload_candidates(missing):
    return [entry for entry in missing if entry.get("origin") == "upload"]


def describe(entry):
    name = entry.get("name") or entry.get("title")

    if name:
        return name

    mime_type = entry.get("mime_type")

    if mime_type:
        return f"Untitled {mime_type}"

    return "Unnamed file"


def summarize(wanted):
    saved = 0
    skipped = 0

    for entries in wanted.values():
        entry = entries[0]

        if entry.get("path"):
            saved += 1
        else:
            skipped += 1

    return saved, skipped
