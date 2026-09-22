from dotenv import load_dotenv
import os
import json
import re
import time

from openai import OpenAI

from app.services.codeblocks import normalize_newlines

load_dotenv()

SECTION_KEYS = ("overview", "key_decisions", "problems_solutions", "technical_details")

# Headings the model uses when it ignores the JSON instruction and writes prose.
SECTION_HEADINGS = {
    "overview": ("overview", "section 1 overview", "1 overview"),
    "key_decisions": ("key decisions", "key_decisions", "section 2 key decisions", "2 key decisions"),
    "problems_solutions": (
        "problems and solutions",
        "problems solutions",
        "problems_solutions",
        "section 3 problems and solutions",
        "3 problems and solutions",
    ),
    "technical_details": (
        "technical details",
        "technical_details",
        "section 4 technical details",
        "4 technical details",
    ),
}

MODEL = "openai/gpt-oss-120b"
BASE_URL = "https://api.groq.com/openai/v1"
TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Capacity knobs. Change these when the API key, tier or model changes.
#
# The request the provider bills is (prompt + reserved answer), and on Groq's
# free tier that total must stay under the tokens-per-minute limit, so the
# prompt is trimmed to fit before it is sent. On a bigger key raise
# CONTEXT_TOKEN_LIMIT (and MAX_OUTPUT_TOKENS for a longer document); nothing
# else needs to change.
#
# The companion knob is FINAL_TOP_K in app/services/retrieval.py, which sets
# how many chunks are retrieved per section.
# ---------------------------------------------------------------------------
CONTEXT_TOKEN_LIMIT = 8000   # tokens per request allowed by the key/model
MAX_OUTPUT_TOKENS = 2500     # reserved for the generated document
SAFETY_MARGIN_TOKENS = 300   # cushion for token-estimate error
MAX_RETRY_WAIT = 30          # seconds; caps the wait after a rate limit

# The model is told this word budget so it spreads the document across all four
# sections instead of being cut off part way through. A reasoning model also
# spends output tokens on thinking, so keep this well under MAX_OUTPUT_TOKENS.
OUTPUT_WORD_BUDGET = int(MAX_OUTPUT_TOKENS * 0.55)

# Chars per token. Measured ~4.5 on this prompt; 3.5 keeps the estimate
# pessimistic so code-heavy chats cannot silently overshoot the limit.
CHARS_PER_TOKEN = 3.5

PROMPT_TOKEN_BUDGET = CONTEXT_TOKEN_LIMIT - MAX_OUTPUT_TOKENS - SAFETY_MARGIN_TOKENS



def strip_fences(raw):
    """Drop a ```json ... ``` wrapper when the model adds one."""

    if not raw.startswith("```"):
        return raw

    raw = re.sub(r"^```[A-Za-z0-9_+.-]*[ \t]*\r?\n?", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw)

    return raw.strip()


def json_object_slice(raw):
    """Return the outermost {...} span, ignoring braces that sit inside strings."""

    start = raw.find("{")

    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(raw)):
        char = raw[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                return raw[start:index + 1]

    return raw[start:]


def escape_control_chars(raw):
    """Escape raw newlines and tabs the model left unescaped inside JSON strings.

    json.loads rejects those with "Invalid control character at: line X column Y",
    which is the usual way an otherwise well-formed answer fails to parse.
    """

    out = []
    in_string = False
    escaped = False

    for char in raw:
        if not in_string:
            if char == '"':
                in_string = True

            out.append(char)
            continue

        if escaped:
            escaped = False
            out.append(char)
        elif char == "\\":
            escaped = True
            out.append(char)
        elif char == '"':
            in_string = False
            out.append(char)
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif ord(char) < 0x20:
            out.append("\\u%04x" % ord(char))
        else:
            out.append(char)

    return "".join(out)


def drop_trailing_commas(raw):
    return re.sub(r",(\s*[}\]])", r"\1", raw)


def loads_relaxed(candidate):
    if not candidate or not candidate.strip():
        return None

    repaired = escape_control_chars(candidate)

    for variant in (candidate, repaired, drop_trailing_commas(repaired)):
        try:
            return json.loads(variant, strict=False)
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def salvage_sections(raw):
    """Last resort: pull each section value out of JSON we still cannot parse."""

    result = {}
    keys = "|".join(SECTION_KEYS)

    for key in SECTION_KEYS:
        match = re.search(
            r'"%s"\s*:\s*"(.*?)"\s*(?:,\s*"(?:%s)"\s*:|}\s*\Z|\Z)' % (key, keys),
            raw,
            re.DOTALL,
        )

        if not match:
            continue

        value = loads_relaxed('"%s"' % match.group(1))
        result[key] = value if isinstance(value, str) else match.group(1)

    return result or None


def heading_key(line):
    """Map a markdown/plain heading line to a section key, or None."""

    if len(line) > 80:
        return None

    cleaned = re.sub(r"[^a-z0-9 ]+", " ", line.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return None

    for key, aliases in SECTION_HEADINGS.items():
        if cleaned in aliases:
            return key

    return None


def salvage_prose(raw):
    """Fall back to splitting a plain-prose answer on its section headings.

    The model occasionally ignores the JSON instruction and just writes the
    document. Rather than failing the whole export, recover the four sections.
    """

    sections = {}
    current = None

    for line in raw.split("\n"):
        key = heading_key(line.strip())

        if key:
            current = key
            sections.setdefault(current, [])
            continue

        if current:
            sections[current].append(line)

    result = {
        key: normalize_newlines("\n".join(lines).strip())
        for key, lines in sections.items()
    }

    return {k: v for k, v in result.items() if v} or None


def parse_sections(raw):
    """Turn the model answer into the four-section dict, tolerating sloppy JSON."""

    raw = strip_fences((raw or "").strip())

    if not raw:
        raise ValueError("LLM returned an empty response")

    result = None

    for candidate in (raw, json_object_slice(raw)):
        parsed = loads_relaxed(candidate)

        if isinstance(parsed, dict):
            result = parsed
            break

    if result is None:
        result = salvage_sections(json_object_slice(raw) or raw)

    if not isinstance(result, dict):
        result = salvage_prose(raw)

    if not isinstance(result, dict):
        raise ValueError("LLM did not return JSON that could be parsed")

    if not any(str(result.get(key) or "").strip() for key in SECTION_KEYS):
        raise ValueError("LLM returned JSON without any of the expected sections")

    return result


def missing_sections(result):
    return [
        key for key in SECTION_KEYS if not str(result.get(key) or "").strip()
    ]


def compact_retrieved(retrieved_data):
    """Keep only what the model needs from the retrieval output.

    retrieve_data returns every chunk wrapped in bookkeeping the model never
    reads - chunk_id, metadata and three float scores - which inflates the
    request far past the API's per-minute token limit. Send the chunk text only.
    """

    if not isinstance(retrieved_data, dict):
        return retrieved_data

    compact = {}

    for section, items in retrieved_data.items():
        texts = []
        seen = set()

        for item in items or []:
            text = item.get("text") if isinstance(item, dict) else item
            text = (text or "").strip()
            key = " ".join(text.split())

            if not text or key in seen:
                continue

            seen.add(key)
            texts.append(text)

        if texts:
            compact[section] = texts

    # Deliberately no fallback to retrieved_data: returning the raw items would
    # smuggle the metadata and scores back into the prompt and skip the budget.
    return compact


def estimate_tokens(text):
    if not text:
        return 0

    return int(len(text) / CHARS_PER_TOKEN) + 1


def truncate_to_tokens(text, max_tokens):
    """Cut text down to roughly max_tokens, preferring a sentence boundary."""

    if max_tokens <= 0:
        return ""

    limit = int(max_tokens * CHARS_PER_TOKEN)

    if len(text) <= limit:
        return text

    clipped = text[:limit]

    # Prefer to end on a sentence, then on a word, so the model is not handed
    # a half-written token sequence.
    for boundary in (clipped.rfind(". "), clipped.rfind("\n"), clipped.rfind(" ")):
        if boundary > limit * 0.6:
            clipped = clipped[:boundary]
            break

    return clipped.rstrip() + " [trimmed]"


def fit_sections(sections, budget):
    """Trim retrieved chunks so the whole payload fits `budget` tokens.

    Chunks arrive best-first from retrieval, so they are taken in rank order and
    the budget is shared between sections round-robin: every section keeps its
    best chunk before any section gets a second one. A conversation long enough
    to exhaust its own context window will always overflow the budget, so this
    decides what to drop instead of letting the provider reject the request.
    """

    if not isinstance(sections, dict) or not sections:
        return {}

    if budget <= 0:
        return {}

    kept = {key: [] for key in sections}
    # Room guaranteed to each section, so a long section 1 cannot starve
    # section 4 of its best chunk.
    share = max(1, budget // len(sections))
    deepest = max((len(texts) for texts in sections.values()), default=0)
    used = 0

    for rank in range(deepest):
        for key, texts in sections.items():
            if rank >= len(texts):
                continue

            text = texts[rank]
            cost = estimate_tokens(text)
            room = budget - used

            if cost <= room and (rank > 0 or cost <= share):
                kept[key].append(text)
                used += cost
                continue

            # Never leave a section empty: clip its best chunk to fit.
            if not kept[key]:
                clipped = truncate_to_tokens(text, min(share, room))

                if clipped:
                    kept[key].append(clipped)
                    used += estimate_tokens(clipped)

    return {key: texts for key, texts in kept.items() if texts}


def build_payload(retrieved_data):
    """Shape the retrieval output into the JSON the prompt carries."""

    sections = compact_retrieved(retrieved_data)

    if not isinstance(sections, dict) or not sections:
        raise ValueError("Retrieved data contained no usable chunk text")

    # Measure the instructions with an empty payload, so the chunk budget is
    # whatever is left over after the fixed part of the prompt.
    overhead = estimate_tokens(build_prompt("{}"))
    fitted = fit_sections(sections, PROMPT_TOKEN_BUDGET - overhead)

    report = {
        "sections": {key: len(value) for key, value in fitted.items()},
        "dropped": {
            key: len(sections.get(key) or []) - len(fitted.get(key) or [])
            for key in sections
        },
    }

    return json.dumps(fitted, ensure_ascii=False), report


def is_rate_limit(error):
    return "rate_limit" in str(error).lower() or "429" in str(error)


def oversized_request(error):
    """True when one request is itself bigger than the limit allows."""

    text = str(error).lower()

    return "request too large" in text or "reduce your message size" in text


def retry_delay(error, attempt):
    """Seconds to wait before retrying, honouring a Retry-After when given."""

    wait = 2 ** attempt

    headers = getattr(getattr(error, "response", None), "headers", None)

    if headers:
        try:
            wait = max(wait, float(headers.get("retry-after") or 0))
        except (TypeError, ValueError):
            pass

    if is_rate_limit(error):
        wait = max(wait, 5)

    return min(wait, MAX_RETRY_WAIT)


def describe_failure(error, budget):
    """Explain a give-up in terms the caller can act on."""

    if oversized_request(error):
        return (
            "The request is larger than the API limit "
            f"({CONTEXT_TOKEN_LIMIT} tokens). Lower FINAL_TOP_K in "
            "app/services/retrieval.py, or raise CONTEXT_TOKEN_LIMIT in "
            f"app/services/llm.py if the key allows more. Sent: {budget}"
        )

    if is_rate_limit(error):
        return (
            "The API rate limit is currently exhausted. Wait a minute and "
            f"export again. Underlying error: {error}"
        )

    return f"LLM request failed after {MAX_ATTEMPTS} attempts: {error}"


def build_prompt(payload):
    return f"""
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
        Write as much as the retrieved chunks justify, within the length budget below.
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
        LENGTH BUDGET (hard limit - the reply is cut off beyond it):
        The four sections together must stay under about {OUTPUT_WORD_BUDGET} words.
        Divide that allowance across the four sections in proportion to how much
        information each one actually has, and always finish all four. A complete
        shorter document is worth more than a detailed one that stops mid-sentence,
        because anything past the limit is discarded.
        Do not artificially add content just to fill the budget. The amount of output must depend entirely on the amount of useful information present in the retrieved chunks.

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

        Return ONLY a single valid JSON object.
        No markdown fences, no explanation before or after it.

        Use exactly this structure:

        {{
          "overview": "",
          "key_decisions": "",
          "problems_solutions": "",
          "technical_details": ""
        }}

        JSON STRING RULES (mandatory - this output is parsed by a machine):
        - Each section value must be ONE JSON string.
        - Write every line break inside a value as the two characters \\n.
          Never press Enter inside a string value and never emit a literal tab.
        - Escape every double quote inside a value as \\" or use single quotes instead.
        - Escape every backslash inside a value as \\\\.
        - No trailing commas, no comments, no extra keys.

        Each value should contain the complete, detailed content for that section.

        Do not create additional top-level sections.

        Do not omit a section.

        If a section has very little relevant information, keep it short rather than inventing information.

        --------------------------------------------------
        INPUT
        --------------------------------------------------

        Now process the following retrieved JSON.
        Each key is a section and each value is the list of chunks retrieved for it.
        Some chunks may end with "[trimmed]" because they did not fit the request
        budget. Use what is there and never guess at the missing part:
        {payload}

    """


def openai_llm(retrieved_data):

    # with open(retrieved_file, 'r', encoding="utf-8") as file:
    #     retrieved_data = json.load(file)

    payload, budget = build_payload(retrieved_data)
    prompt = build_prompt(payload)

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")

    if not api_key:
        raise RuntimeError("No LLM API key configured (set GROQ_API_KEY)")

    client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=TIMEOUT_SECONDS)

    result = None
    last_error = None

    # The answer is retried on an unusable reply too, not just on a failed
    # request: the model occasionally returns text that is not valid JSON.
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.responses.create(
                model=MODEL,
                input=prompt,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
            result = parse_sections(response.output_text or "")

            # A reply cut off by the output cap parses but loses whole sections.
            # Retry once rather than exporting a half document.
            if missing_sections(result) and attempt < MAX_ATTEMPTS - 1:
                last_error = ValueError(
                    "answer was cut off before %s"
                    % ", ".join(missing_sections(result))
                )
                result = None
                continue

            break
        except Exception as e:
            last_error = e

            if oversized_request(e):
                # Retrying cannot help: the request alone exceeds the limit.
                break

            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(retry_delay(e, attempt))

    if result is None:
        raise RuntimeError(describe_failure(last_error, budget))

    gaps = missing_sections(result)

    if gaps:
        # Still better than no document, but say so instead of shipping a
        # silently empty section.
        print(
            "openai_llm: sections left empty after %d attempts: %s "
            "(raise MAX_OUTPUT_TOKENS or lower FINAL_TOP_K)"
            % (MAX_ATTEMPTS, ", ".join(gaps))
        )

    for key in SECTION_KEYS:
        result[key] = normalize_newlines(str(result.get(key) or ""))

    return result

# openai_llm()
