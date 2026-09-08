import json
import re
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "output" / "memory_export.pdf"

def clean_text(text):
    replacements = {
        "\u2011": "-",  # non-breaking hyphen
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2212": "-",  # minus sign
        "\u00a0": " ",  # non-breaking space
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
    }

    for old, new in replacements.items():
        text = text.replace(old, new)
    return text



def markdown_to_reportlab(text):

    text = clean_text(str(text))
    text = escape(text)
    
    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"<b>\1</b>",
        text
    )

    text = re.sub(
        r"^\s*[-*]\s+(.*)$",
        r"• \1",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"^\s*(\d+)\.\s+(.*)$",
        r"<b>\1.</b> \2",
        text,
        flags=re.MULTILINE
    )

    return text.replace("\n", "<br/>")


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)

    canvas.drawString(
        20 * mm,
        10 * mm,
        "MemoryExporter"
    )

    canvas.drawRightString(
        A4[0] - 20 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()





def generate_pdf(
    title,
    source_url,
    platform,
    final_data,
    output_file= OUTPUT_FILE
):
    if isinstance(final_data, str):
        data = json.loads(final_data)
    elif isinstance(final_data, dict):
        data = final_data
    else:
        raise TypeError(
            "final_data must be a JSON string or dictionary"
        )

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="MemoryExporter",
        author="MemoryExporter",
        subject="AI Agent Conversation Memory",
        keywords="AI, Agent Memory, RAG, Conversation, Memory Transfer"
    )

    styles = getSampleStyleSheet()

    main_title_style = ParagraphStyle(
        "MainTitle",
        parent=styles["Title"],
        fontSize=26,
        leading=32,
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    description_style = ParagraphStyle(
        "Description",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading1"],
        fontSize=17,
        leading=22,
        spaceBefore=15,
        spaceAfter=12
    )

    subsection_style = ParagraphStyle(
        "SubSection",
        parent=styles["Heading2"],
        fontSize=12.5,
        leading=17,
        spaceBefore=10,
        spaceAfter=7
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=16,
        spaceAfter=8
    )

    story = []

    story.append(
        Paragraph(
            "AI CHAT EXPORTER",
            main_title_style
        )
    )

    story.append(
        Paragraph(
            "AI AGENT MEMORY TRANSFER DOCUMENT",
            subtitle_style
        )
    )

    description = """
    This document contains knowledge and context extracted from a
    previous conversation between a user and an AI agent. It is
    designed to help another AI agent understand the previous
    conversation, the user's context, decisions, problems,
    solutions, and technical information, and continue assisting
    the user with appropriate continuity.
    """

    story.append(
        Paragraph(
            description,
            description_style
        )
    )

    story.append(
        Paragraph(
            "INSTRUCTIONS FOR THE RECEIVING AI AGENT",
            section_style
        )
    )

    instruction = """
    This document represents transferred memory from a previous AI
    conversation. Use the information contained in this document as
    contextual memory when assisting the user. Understand the previous
    conversation and maintain continuity where appropriate. Do not
    assume information that is not present in this document. If
    required information is missing, ask the user instead of inventing
    or guessing it.
    """

    story.append(
        Paragraph(
            instruction,
            body_style
        )
    )

    story.append(
        Paragraph(
            "DETAILS",
            section_style
        )
    )

    generated_at = datetime.now().strftime(
        "%d %B %Y, %H:%M"
    )

    details = [
        ["Title", escape(str(title))],
        ["Source URL", escape(str(source_url))],
        ["Platform", escape(str(platform))],
        ["Generated", generated_at]
    ]

    table = Table(
        details,
        colWidths=[35 * mm, 125 * mm]
    )

    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
        ])
    )

    story.append(table)
    story.append(Spacer(1, 15))

    sections = [
        ("1. OVERVIEW", "overview"),
        ("2. KEY DECISIONS", "key_decisions"),
        ("3. PROBLEMS & SOLUTIONS", "problems_solutions"),
        ("4. TECHNICAL DETAILS", "technical_details")
    ]

    for heading, key in sections:

        story.append(
            Paragraph(
                heading,
                section_style
            )
        )

        content = data.get(key, "")

        if not content:
            story.append(
                Paragraph(
                    "No information available for this section.",
                    body_style
                )
            )
            continue

        for line in str(content).split("\n"):

            line = line.strip()

            if not line:
                story.append(Spacer(1, 4))
                continue

            if line.startswith("### "):
                heading_text = escape(line[4:].strip())

                story.append(
                    Paragraph(
                        heading_text,
                        subsection_style
                    )
                )

                continue

            if line.startswith("## "):
                heading_text = escape(line[3:].strip())

                story.append(
                    Paragraph(
                        heading_text,
                        subsection_style
                    )
                )

                continue

            story.append(
                Paragraph(
                    markdown_to_reportlab(line),
                    body_style
                )
            )

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    return str(output_file)


def run():
    chat_data = Path(__file__).parent.parent/"demo_data"/"data8"/"chat_data.json"
    final_data = Path(__file__).parent.parent/"demo_data"/"data8"/"final_data.json"

    with open(chat_data, 'r', encoding="utf-8") as file:
        data = json.load(file)

    with open(final_data, 'r', encoding="utf-8") as file:
        final_data = json.load(file)

    title = data.get("title")
    source_url = data.get("source_url")
    platform = data.get("platform")

    result = generate_pdf(title=title, source_url=source_url, platform=platform, final_data=final_data) 

    print(result)

# run()