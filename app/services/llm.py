from dotenv import load_dotenv
import os
import json
import re
import time

from openai import OpenAI

from app.services.codeblocks import normalize_newlines

load_dotenv()

SECTION_KEYS = ("overview", "key_decisions", "problems_solutions", "technical_details")

MODEL = "openai/gpt-oss-120b"
BASE_URL = "https://api.groq.com/openai/v1"
TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 3
# retrieved_file = app_dir/"demo_data"/"chatgpt"/folder/"retrieved_data.json"
# prompt_file = app_dir/"llm_prompt"/"prompt.txt"



def openai_llm(retrieved_data):

    # with open(retrieved_file, 'r', encoding="utf-8") as file:
    #     retrieved_data = json.load(file)

    prompt = f"""
        You are a document generation and information-preservation system where you have to generate a data such that if sending this data other agent can understand all the chats the has been done previously with another agent.
        make a data such that agent gets understand all the data and start working as a previous chat agent.

        You will receive RETRIEVED JSON containing conversation chunks grouped into exactly four topics:
        1. overview 
        2. key_decisions
        3. problems_solutions
        4. technical_details
        Your task is to transform ONLY the information contained in these retrieved chunks into a detailed, well-written document with exactly these same four sections.
        IMPORTANT:
        The retrieved chunks are the SOURCE OF TRUTH.
        Write as much as the retrieved chunks justify. Do not truncate to a fixed line count.
        Code blocks and diagrams are carried into the final document separately and verbatim, so you
        do not need to reproduce them here - describe what they do and refer to them by name.
        Do NOT add information from your own knowledge.
        Do NOT make assumptions.
        Do NOT infer information that is not explicitly present.
        Do NOT hallucinate.
        Do NOT change the meaning of the original information.
        Remove all internal retrieval metadata, including chunk IDs, chunk numbers, source labels, and references such as (Chunk-009), from the final output.

        Your primary goal is INFORMATION PRESERVATION.
        Do not unnecessarily summarize the retrieved chunks. Preserve as much useful information as possible so that no important information from the retrieved data is lost.
        If a chunk contains multiple useful points, preserve ALL of those points.
        If different chunks contain different information about the same topic, combine all of the information into the appropriate section.
        If multiple chunks contain the same information, mention it only once unless repeating it is necessary for clarity or context.
        Do not remove a detail merely because it appears less important. If it contains useful information related to the section, preserve it.
        The final document should normally be detailed enough to produce approximately 2-7 pages of content depending on how much information exists in the retrieved JSON.
        Do not artificially add content just to increase the page count. The amount of output must depend entirely on the amount of useful information present in the retrieved chunks.

        --------------------------------------------------
        SECTION RULES
        --------------------------------------------------

        SECTION 1 — OVERVIEW
        Use ONLY information from the "overview" retrieved chunks.
        Create a detailed and coherent explanation of the overall subject discussed in the conversations.
        Preserve:
        - Main purpose
        - Main idea
        - Project/product concept
        - Overall workflow
        - Important goals
        - Important characteristics
        - Overall conclusions
        - Any other relevant information present in the overview chunks

        Do not introduce information from other sections unless the same information is necessary to make the overview understandable.
        --------------------------------------------------

        SECTION 2 — KEY DECISIONS

        Use ONLY information from the "key_decisions" retrieved chunks.
        Extract and explain every important decision, recommendation, direction, architectural choice, or strategic decision present in these chunks.
        Preserve:
        - What decision was made
        - Why it was suggested or chosen
        - Important reasoning
        - Recommended changes
        - Architecture decisions
        - Product decisions
        - Future direction
        - Evaluation decisions
        - Any other decision-related information present in the chunks
        Do not reduce several distinct decisions into one vague statement.
        --------------------------------------------------

        SECTION 3 — PROBLEMS AND SOLUTIONS

        Use ONLY information from the "problems_solutions" retrieved chunks.
        Preserve every problem, limitation, challenge, and corresponding solution or recommendation found in the chunks.
        For each problem, explain where possible:
        Problem:
        What was the problem or limitation?
        Solution:
        What solution, improvement, or recommendation was provided?
        Reason:
        Why was that solution relevant, if the retrieved data explains it?
        Do not invent solutions for problems where no solution is present in the retrieved data.

        --------------------------------------------------

        SECTION 4 — TECHNICAL DETAILS

        Use ONLY information from the "technical_details" retrieved chunks.
        Preserve all relevant technical information contained in these chunks.
        Include:
        - Technologies
        - Programming concepts
        - Architecture
        - RAG pipeline
        - Retrieval
        - LLM processing
        - Data processing
        - JSON/structured data
        - PDF generation
        - Agent memory
        - APIs
        - Technical workflows
        - Technical recommendations
        - Any other technical information explicitly present in the retrieved chunks

        Explain technical information clearly and in sufficient detail.
        Do not replace technical details with a short summary.
        --------------------------------------------------
        ANTI-HALLUCINATION RULES
        --------------------------------------------------
        1. The retrieved JSON is the ONLY source of information.
        2. Never use outside knowledge.
        3. Never guess missing information.
        4. Never create names, technologies, features, dates, numbers, or facts that are not present in the retrieved data.
        5. If something is incomplete in the retrieved chunks, do not complete it using your own knowledge.
        6. If a chunk is truncated, preserve only the information that is actually available.
        7. Do not treat your own reasoning as a fact.
        8. Do not "improve" the original information by adding unsupported details.

        --------------------------------------------------
        DUPLICATION RULES
        --------------------------------------------------
        Avoid unnecessary repetition.

        If the same information appears in multiple retrieved chunks:
        - Combine it into one clear explanation.
        - Keep the most complete version.
        - Do not repeat the same paragraph multiple times.
        However, repetition IS allowed when:
        - The information has a different meaning in another section.
        - It is necessary to explain the section properly.
        - Removing it would make that section incomplete or confusing.
        The goal is:
        MAXIMUM INFORMATION PRESERVATION
        +
        MINIMUM UNNECESSARY REPETITION
        --------------------------------------------------
        WRITING RULES
        --------------------------------------------------
        Write the final document in professional, clear, natural language.

        Use:
        - Headings
        - Subheadings where useful
        - Paragraphs
        - Bullet points where they improve readability
        - Numbered lists where appropriate

        Do not turn everything into bullet points.
        Important explanations should be written as proper paragraphs.
        Do not write conversational phrases such as:
        "Here is your document"
        "I analyzed the data"
        "Based on the information you provided"

        Start directly with the document content.

        Do not mention these instructions in the output.

        --------------------------------------------------
        OUTPUT FORMAT
        --------------------------------------------------

        Return ONLY valid JSON.

        Use exactly this structure:

        "overview": "",
        "key_decisions": "",
        "problems_solutions": "",
        "technical_details": ""
        

        Each value should contain the complete, detailed content for that section.

        Do not create additional top-level sections.

        Do not omit a section.

        If a section has very little relevant information, keep it short rather than inventing information.

        --------------------------------------------------
        INPUT
        --------------------------------------------------

        Now process the following retrieved JSON:
        {json.dumps(retrieved_data, ensure_ascii=False, indent=2)}

    """

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")

    if not api_key:
        raise RuntimeError("No LLM API key configured (set GROQ_API_KEY)")

    client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=TIMEOUT_SECONDS)

    response = None
    last_error = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.responses.create(model=MODEL, input=prompt)
            break
        except Exception as e:
            last_error = e

            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(f"LLM request failed after {MAX_ATTEMPTS} attempts: {e}")

            time.sleep(2 ** attempt)

    if response is None:
        raise RuntimeError(f"LLM request failed: {last_error}")

    raw = (response.output_text or "").strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```[A-Za-z0-9_+-]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)

        if not match:
            raise ValueError("LLM did not return JSON")

        result = json.loads(match.group(0))

    if not isinstance(result, dict):
        raise ValueError("LLM returned JSON that is not an object")

    for key in SECTION_KEYS:
        result[key] = normalize_newlines(str(result.get(key) or ""))

    return result

# openai_llm()
