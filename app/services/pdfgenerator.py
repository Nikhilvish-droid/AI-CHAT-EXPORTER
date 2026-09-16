import io
import json
import re
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    XPreformatted,
    KeepTogether,
    PageBreak,
)
from reportlab.platypus.flowables import HRFlowable

from app.services import assets as assetlib
from app.services.codeblocks import normalize_newlines

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "output" / "memory_export.pdf"

PAGE_WIDTH = A4[0]
MARGIN = 20 * mm
# SimpleDocTemplate pads its frame by 6pt on each side, so the drawable width
# is narrower than the margin box. Ignoring that padding makes every full-width
# table 12pt too wide for its frame.
FRAME_PADDING = 6

CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN) - (2 * FRAME_PADDING)

# A table row cannot be split across pages unless the row itself is splittable,
# so text placed in a cell is capped. A long asset title (an image-generation
# prompt, say) would otherwise build one row taller than the whole page.
MAX_CELL_CHARS = 300

MAX_IMAGE_WIDTH = 150 * mm
MAX_IMAGE_HEIGHT = 185 * mm

INK = colors.HexColor("#1F1F1D")
MUTED = colors.HexColor("#6B6A64")
RULE = colors.HexColor("#D9D8D1")
ACCENT = colors.HexColor("#185FA5")
CODE_BG = colors.HexColor("#F6F6F3")
CODE_BORDER = colors.HexColor("#E2E1D9")
TABLE_HEAD = colors.HexColor("#F1EFE8")

BOX_DRAWING = set("┌┐└┘│─├┤┬┴┼╔╗╚╝║═╠╣╦╩╬▲▼◄►↓↑←→")

ASCII_ART_CHARS = set("+-=|_/\\<>v^ ")

ASCII_ART_PATTERN = re.compile(r"[+|]-{2,}|-{2,}[+|]|\+={2,}|={2,}\+")

TABLE_ROW_PATTERN = re.compile(r"^\|.*\|$")

CODE_FONT_SIZE = 8.5
CODE_CHAR_WIDTH = 0.6
CODE_PADDING = 8
TARGET_DPI = 170
KEEP_TOGETHER_MAX_LINES = 26

BOX_TRANSLATION = {
    0x250C: "+", 0x2510: "+", 0x2514: "+", 0x2518: "+",
    0x251C: "+", 0x2524: "+", 0x252C: "+", 0x2534: "+", 0x253C: "+",
    0x2554: "+", 0x2557: "+", 0x255A: "+", 0x255D: "+",
    0x2560: "+", 0x2563: "+", 0x2566: "+", 0x2569: "+", 0x256C: "+",
    0x2500: "-", 0x2550: "=", 0x2504: "-", 0x2508: "-",
    0x2502: "|", 0x2551: "|", 0x2506: "|", 0x250A: "|",
    0x2191: "^", 0x2193: "v", 0x2190: "<", 0x2192: ">",
    0x25B2: "^", 0x25BC: "v", 0x25C4: "<", 0x25BA: ">",
    0x2022: "*", 0x25A0: "#", 0x25AA: "*",
}


def ascii_safe(line):
    return str(line).translate(BOX_TRANSLATION)

SVG_CLASS_STYLE = """
text { font-family: Helvetica; }
.t { font-family: Helvetica; font-size: 14px; fill: #3d3d3a; }
.ts { font-family: Helvetica; font-size: 12px; fill: #73726c; }
.th { font-family: Helvetica-Bold; font-size: 14px; fill: #3d3d3a; }
.box { fill: #ffffff; stroke: #b4b2a9; }
.arr { stroke: #73726c; fill: none; }
.leader { stroke: #73726c; fill: none; stroke-dasharray: 2 2; }
.c-gray { fill: #F1EFE8; stroke: #5F5E5A; }
.c-blue { fill: #E6F1FB; stroke: #185FA5; }
.c-teal { fill: #E1F5EE; stroke: #0F6E56; }
.c-purple { fill: #EEEDFE; stroke: #534AB7; }
.c-coral { fill: #FAECE7; stroke: #993C1D; }
.c-pink { fill: #FBEAF0; stroke: #993556; }
.c-green { fill: #EAF3DE; stroke: #3B6D11; }
.c-amber { fill: #FAEEDA; stroke: #854F0B; }
.c-red { fill: #FCEBEB; stroke: #A32D2D; }
.c-gray > rect, .c-blue > rect, .c-teal > rect, .c-purple > rect,
.c-coral > rect, .c-pink > rect, .c-green > rect, .c-amber > rect,
.c-red > rect { fill: inherit; stroke: inherit; }
"""


def clean_text(text):
    replacements = {
        "‑": "-",
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def build_styles():
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "lead": ParagraphStyle(
            "Lead",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=17,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=INK,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "subsection": ParagraphStyle(
            "SubSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=16,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15.5,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=INK,
            backColor=colors.HexColor("#FAEEDA"),
            borderColor=colors.HexColor("#EF9F27"),
            borderWidth=0.5,
            borderPadding=8,
            spaceBefore=6,
            spaceAfter=10,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15.5,
            textColor=INK,
            leftIndent=14,
            bulletIndent=3,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=14,
        ),
        "codelabel": ParagraphStyle(
            "CodeLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            spaceBefore=8,
            spaceAfter=2,
        ),
    }


def code_style(font_size):
    return ParagraphStyle(
        f"Code{font_size}",
        fontName="Courier",
        fontSize=font_size,
        leading=font_size * 1.32,
        textColor=INK,
        backColor=CODE_BG,
        borderColor=CODE_BORDER,
        borderWidth=0.5,
        borderPadding=CODE_PADDING,
        spaceBefore=2,
        spaceAfter=10,
    )


def inline_markup(text):
    text = escape(clean_text(str(text)))

    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<link href="\2" color="#185FA5">\1</link>',
        text,
    )

    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", text)

    text = re.sub(
        r"`([^`\n]+?)`",
        r'<font face="Courier" size="9" color="#0F6E56">\1</font>',
        text,
    )

    return text


def is_art_line(line):
    stripped = line.strip()

    if not stripped:
        return False

    if sum(1 for ch in stripped if ch in BOX_DRAWING) >= 3:
        return True

    if TABLE_ROW_PATTERN.match(stripped) and stripped.count("|") >= 3:
        return False

    if ASCII_ART_PATTERN.search(stripped):
        return True

    if len(stripped) >= 6 and all(ch in ASCII_ART_CHARS for ch in stripped):
        return sum(1 for ch in stripped if ch in "+-=|") >= 4

    return False


def split_blocks(content):
    lines = normalize_newlines(str(content)).split("\n")
    blocks = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            index += 1
            body = []

            while index < len(lines) and not lines[index].strip().startswith("```"):
                body.append(lines[index])
                index += 1

            index += 1
            blocks.append(("code", {"language": language, "lines": body}))
            continue

        if is_art_line(line):
            body = []

            while index < len(lines) and (is_art_line(lines[index]) or (lines[index].strip() and body)):
                if not is_art_line(lines[index]) and not lines[index].strip():
                    break
                body.append(lines[index])
                index += 1

            blocks.append(("art", {"lines": body}))
            continue

        if not stripped:
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)

        if heading:
            blocks.append(("heading", {"text": heading.group(2)}))
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            body = []

            while index < len(lines) and lines[index].strip().startswith("|"):
                body.append(lines[index].strip())
                index += 1

            blocks.append(("table", {"lines": body}))
            continue

        bullet = re.match(r"^\s*[-*+]\s+(.*)$", line)

        if bullet:
            blocks.append(("bullet", {"text": bullet.group(1), "marker": "•"}))
            index += 1
            continue

        numbered = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)

        if numbered:
            blocks.append(("bullet", {"text": numbered.group(2), "marker": f"{numbered.group(1)}."}))
            index += 1
            continue

        start = index
        body = [stripped]
        index += 1

        while index < len(lines):
            nxt = lines[index]

            if not nxt.strip():
                break
            if nxt.strip().startswith(("```", "#", "|")):
                break
            if re.match(r"^\s*([-*+]|\d+[.)])\s+", nxt):
                break
            if is_art_line(nxt):
                break

            body.append(nxt.strip())
            index += 1

        if body:
            blocks.append(("para", {"text": " ".join(body)}))

        if index <= start:
            index = start + 1

    return blocks


def wrap_code(lines, limit):
    wrapped = []

    for line in lines:
        line = line.rstrip()

        if len(line) <= limit:
            wrapped.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        pad = " " * min(indent + 2, limit - 10)
        remaining = line

        while len(remaining) > limit:
            wrapped.append(remaining[:limit])
            remaining = pad + remaining[limit:]

        wrapped.append(remaining)

    return wrapped


def render_code(block, styles):
    lines = [line.rstrip() for line in block["lines"]]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return []

    art_lines = sum(1 for line in lines if is_art_line(line))
    usable = CONTENT_WIDTH - (2 * CODE_PADDING)

    if art_lines and art_lines >= len(lines) / 3:
        widest = max(len(line) for line in lines)
        size = max(4.5, round(min(9.0, usable / (CODE_CHAR_WIDTH * max(widest, 1))), 2))
    else:
        size = CODE_FONT_SIZE
        limit = max(20, int(usable / (CODE_CHAR_WIDTH * size)))
        lines = wrap_code(lines, limit)

    flowables = []
    language = (block.get("language") or "").strip()

    if language and not art_lines:
        flowables.append(Paragraph(escape(language.upper()), styles["codelabel"]))

    flowables.append(
        XPreformatted("\n".join(escape(ascii_safe(line)) for line in lines), code_style(size))
    )

    if len(lines) > KEEP_TOGETHER_MAX_LINES:
        return flowables

    return [KeepTogether(flowables)] if len(flowables) > 1 else flowables


def render_art(block, styles):
    lines = [line.rstrip() for line in block["lines"]]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return []

    widest = max(len(line) for line in lines)
    usable = CONTENT_WIDTH - (2 * CODE_PADDING)
    size = min(9.0, usable / (CODE_CHAR_WIDTH * max(widest, 1)))
    size = max(4.5, round(size, 2))

    return [
        KeepTogether([
            XPreformatted(
                "\n".join(escape(ascii_safe(line)) for line in lines),
                code_style(size),
            )
        ])
    ]


def render_table(block, styles):
    rows = []

    for line in block["lines"]:
        if re.fullmatch(r"\|[\s:|-]+\|", line):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]

        if cells:
            rows.append(cells)

    if not rows:
        return []

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]

    data = [[Paragraph(inline_markup(cell), styles["body"]) for cell in row] for row in rows]
    col_width = CONTENT_WIDTH / width

    # splitInRow lets a tall row break across pages instead of raising
    # LayoutError; conversation tables are not truncated to make them fit.
    table = Table(data, colWidths=[col_width] * width, repeatRows=1, splitInRow=1)

    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    return [table, Spacer(1, 10)]


def render_markdown(content, styles):
    flowables = []

    for kind, block in split_blocks(content):
        if kind == "code":
            flowables.extend(render_code(block, styles))
        elif kind == "art":
            flowables.extend(render_art(block, styles))
        elif kind == "table":
            flowables.extend(render_table(block, styles))
        elif kind == "heading":
            flowables.append(Paragraph(inline_markup(block["text"]), styles["subsection"]))
        elif kind == "bullet":
            flowables.append(
                Paragraph(
                    inline_markup(block["text"]),
                    styles["bullet"],
                    bulletText=block["marker"],
                )
            )
        else:
            flowables.append(Paragraph(inline_markup(block["text"]), styles["body"]))

    return flowables


def section_heading(text, styles):
    return KeepTogether([
        Spacer(1, 6),
        Paragraph(escape(text), styles["section"]),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceBefore=2, spaceAfter=10),
    ])


def style_svg(svg_text):
    if "<style" in svg_text:
        return svg_text

    for token, value in (
        ("var(--t)", "#73726c"),
        ("var(--p)", "#3d3d3a"),
        ("var(--s)", "#73726c"),
        ("var(--b)", "#b4b2a9"),
        ("var(--bg2)", "#ffffff"),
    ):
        svg_text = svg_text.replace(token, value)

    match = re.search(r"<svg[^>]*>", svg_text)

    if not match:
        return svg_text

    return (
        svg_text[:match.end()]
        + f"<style>{SVG_CLASS_STYLE}</style>"
        + svg_text[match.end():]
    )


def scaled_size(width, height, max_width=None, max_height=None):
    max_width = max_width or MAX_IMAGE_WIDTH
    max_height = max_height or MAX_IMAGE_HEIGHT

    if not width or not height:
        return max_width, max_height

    ratio = min(max_width / width, max_height / height, 1.0)

    return width * ratio, height * ratio


def svg_flowable(file_path, max_width=None, max_height=None):
    from svglib.svglib import svg2rlg

    styled = style_svg(Path(file_path).read_text(encoding="utf-8"))
    temp_path = Path(file_path).with_suffix(".styled.svg")

    try:
        temp_path.write_text(styled, encoding="utf-8")
        drawing = svg2rlg(str(temp_path))
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass

    if drawing is None:
        return None

    if drawing.width and drawing.height:
        ratio = min(
            (max_width or MAX_IMAGE_WIDTH) / drawing.width,
            (max_height or MAX_IMAGE_HEIGHT) / drawing.height,
            1.0,
        )
        drawing.width *= ratio
        drawing.height *= ratio
        drawing.scale(ratio, ratio)

    return drawing


def downsample(opened, target_px):
    from PIL import Image as PILImage

    width, height = opened.size
    ratio = target_px / float(width)
    size = (max(1, int(width * ratio)), max(1, int(height * ratio)))

    resized = opened.convert("RGB") if opened.mode in ("RGBA", "LA", "P") else opened.copy()

    if opened.mode in ("RGBA", "LA"):
        background = PILImage.new("RGB", opened.size, (255, 255, 255))
        background.paste(opened, mask=opened.split()[-1])
        resized = background

    resized = resized.resize(size, PILImage.LANCZOS)

    buffer = io.BytesIO()
    resized.save(buffer, format="JPEG", quality=82, optimize=True)
    buffer.seek(0)

    return buffer


def image_flowable(entry, base_dir, max_width=None, max_height=None):
    if not entry.get("path"):
        return None

    file_path = base_dir / entry["path"]

    if not file_path.exists():
        return None

    try:
        if entry.get("mime_type") == "image/svg+xml":
            return svg_flowable(file_path, max_width, max_height)

        from PIL import Image as PILImage

        with PILImage.open(file_path) as opened:
            width, height = opened.size
            draw_width, draw_height = scaled_size(width, height, max_width, max_height)

            target_px = int(draw_width / 72.0 * TARGET_DPI)

            if width > target_px * 1.1:
                source = downsample(opened, target_px)
            else:
                source = str(file_path)

        return Image(source, width=draw_width, height=draw_height)
    except Exception:
        return None


def image_grid(embedded, base_dir, styles, columns=2):
    gutter = 6 * mm
    cell_width = (CONTENT_WIDTH - gutter * (columns - 1)) / columns
    cell_height = 50 * mm

    cells = []

    for entry in embedded:
        flowable = image_flowable(entry, base_dir, cell_width - 4 * mm, cell_height)

        if flowable is None:
            continue

        cells.append([
            flowable,
            Paragraph(escape(clip_cell(assetlib.describe(entry))), styles["caption"]),
        ])

    if not cells:
        return []

    rows = []

    for start in range(0, len(cells), columns):
        row = cells[start:start + columns]
        row += [""] * (columns - len(row))
        rows.append(row)

    table = Table(
        rows,
        colWidths=[cell_width] * columns,
        hAlign="LEFT",
        splitInRow=1,
    )

    table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), gutter / 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ])
    )

    return [table]


def verbatim_block(item, styles):
    lines = normalize_newlines(item.get("code") or "").split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return []

    usable = CONTENT_WIDTH - (2 * CODE_PADDING)
    widest = max(len(line) for line in lines)

    if item.get("kind") == "diagram":
        size = max(4.5, round(min(9.0, usable / (CODE_CHAR_WIDTH * max(widest, 1))), 2))
    else:
        size = CODE_FONT_SIZE

        if widest > usable / (CODE_CHAR_WIDTH * size):
            fitted = usable / (CODE_CHAR_WIDTH * widest)

            if fitted >= 6.0:
                size = round(fitted, 2)
            else:
                lines = wrap_code(lines, max(20, int(usable / (CODE_CHAR_WIDTH * size))))

    label = item.get("language") or "text"

    if item.get("kind") == "diagram":
        label = "DIAGRAM"

    flowables = [
        Paragraph(escape(label.upper()), styles["codelabel"]),
        XPreformatted(
            "\n".join(escape(ascii_safe(line)) for line in lines),
            code_style(size),
        ),
    ]

    if len(lines) > KEEP_TOGETHER_MAX_LINES:
        return flowables

    return [KeepTogether(flowables)]


def page_furniture(canvas, doc):
    canvas.saveState()

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 14 * mm, PAGE_WIDTH - MARGIN, 14 * mm)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 10 * mm, "AI Chat Exporter  ·  Agent memory transfer")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 10 * mm, f"Page {doc.page}")

    canvas.restoreState()


def details_table(title, source_url, platform, generated_at):
    rows = [
        ["Title", escape(str(title or "Untitled conversation"))],
        ["Source", escape(str(source_url or "-"))],
        ["Platform", escape(str(platform or "-")).title()],
        ["Generated", generated_at],
    ]

    body = ParagraphStyle(
        "Cell",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=INK,
    )

    data = [[row[0], Paragraph(row[1], body)] for row in rows]

    table = Table(data, colWidths=[32 * mm, CONTENT_WIDTH - 32 * mm])

    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("BACKGROUND", (0, 0), (0, -1), TABLE_HEAD),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    return table


def clip_cell(text, limit=MAX_CELL_CHARS):
    """Keep a table cell short enough that its row still fits on a page."""

    text = str(text or "")

    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + "..."


def missing_table(missing, styles):
    cell = ParagraphStyle(
        "MissingCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=INK,
    )

    rows = [["File", "Type", "Why it is not included"]]

    for entry in missing:
        reason = entry.get("skip_reason")

        if reason == assetlib.SKIP_NOT_EMBEDDABLE:
            label = "Format cannot be embedded in a PDF"
        elif reason == assetlib.SKIP_TOO_LARGE:
            label = "Larger than the embed limit"
        else:
            label = "Not available in the shared link"

        if entry.get("origin") == "upload":
            label += " (uploaded by the user)"

        rows.append([
            Paragraph(escape(clip_cell(assetlib.describe(entry))), cell),
            Paragraph(escape(clip_cell(entry.get("mime_type") or "unknown")), cell),
            Paragraph(label, cell),
        ])

    table = Table(
        rows,
        colWidths=[55 * mm, 40 * mm, CONTENT_WIDTH - 95 * mm],
        repeatRows=1,
        splitInRow=1,
    )

    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    return table


def generate_pdf(
    title,
    source_url,
    platform,
    final_data,
    output_file=OUTPUT_FILE,
    assets=None,
    code_blocks=None,
):
    if isinstance(final_data, str):
        data = json.loads(final_data)
    elif isinstance(final_data, dict):
        data = final_data
    else:
        raise TypeError("final_data must be a JSON string or dictionary")

    assets = assets or {"embedded": [], "missing": []}
    embedded = assets.get("embedded") or []
    missing = assets.get("missing") or []
    reupload = assetlib.reupload_candidates(missing)

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=24 * mm,
        title=str(title or "Agent memory transfer"),
        author="AI Chat Exporter",
        subject="AI Agent Conversation Memory",
        keywords="AI, Agent Memory, RAG, Conversation, Memory Transfer",
    )

    styles = build_styles()
    story = []

    story.append(Paragraph("AI CHAT EXPORTER", styles["title"]))
    story.append(Paragraph("AGENT MEMORY TRANSFER DOCUMENT", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=16))

    story.append(
        Paragraph(
            "This document carries the knowledge and context of a previous "
            "conversation between a user and an AI assistant, so that another "
            "assistant can continue the work without losing continuity.",
            styles["lead"],
        )
    )

    story.append(
        details_table(
            title,
            source_url,
            platform,
            datetime.now().strftime("%d %B %Y, %H:%M"),
        )
    )

    story.append(Spacer(1, 18))
    story.append(section_heading("Instructions for the receiving assistant", styles))

    story.append(
        Paragraph(
            "Treat everything below as transferred memory from an earlier "
            "conversation. Use it as context when helping the user, and keep "
            "continuity with the decisions already made. Do not assume anything "
            "that is not written here; if something you need is missing, ask the "
            "user rather than guessing. Once you have read this document, confirm "
            "to the user that you understand the earlier conversation and are "
            "ready to continue from it.",
            styles["body"],
        )
    )

    if reupload:
        names = ", ".join(escape(assetlib.describe(entry)) for entry in reupload)
        count = len(reupload)

        story.append(
            Paragraph(
                f"<b>Action needed.</b> The user attached {count} "
                f"{'file' if count == 1 else 'files'} to the original conversation "
                f"({names}) that could not be recovered from the shared link. Ask the "
                "user to re-upload them before relying on any part of this document "
                "that depends on their contents.",
                styles["note"],
            )
        )

    if missing:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Files not included", styles["subsection"]))
        story.append(missing_table(missing, styles))

    story.append(Spacer(1, 10))

    sections = [
        ("1. Overview", "overview"),
        ("2. Key decisions", "key_decisions"),
        ("3. Problems and solutions", "problems_solutions"),
        ("4. Technical details", "technical_details"),
    ]

    for heading, key in sections:
        story.append(section_heading(heading, styles))

        content = data.get(key)

        if not content or not str(content).strip():
            story.append(
                Paragraph("No information available for this section.", styles["body"])
            )
            continue

        story.extend(render_markdown(content, styles))

    code_blocks = code_blocks or []
    next_section = 5

    if code_blocks:
        story.append(
            section_heading(
                f"{next_section}. Code and diagrams from the conversation",
                styles,
            )
        )
        next_section += 1

        story.append(
            Paragraph(
                "Reproduced exactly as they appeared in the original conversation. "
                "Nothing here has been summarised or shortened.",
                styles["body"],
            )
        )

        for item in code_blocks:
            story.extend(verbatim_block(item, styles))

    grid = image_grid(embedded, BASE_DIR, styles)

    if grid:
        story.append(
            section_heading(f"{next_section}. Images from the conversation", styles)
        )
        story.extend(grid)

    doc.build(story, onFirstPage=page_furniture, onLaterPages=page_furniture)

    return str(output_file)
