# AI Chat Exporter — Agent Memory Transfer

A FastAPI service that turns a **shared AI chat link** (ChatGPT, Gemini, or Claude) into a
**"memory transfer" PDF** — a structured document another AI agent can read to pick up the
conversation where the previous one left off.

You give it a share URL. It scrapes the conversation, runs it through a retrieval pipeline
(chunk → embed → vector store → hybrid search), asks an LLM to reorganize the retrieved
material into four fixed sections, and renders the result as a PDF.

---

## Pipeline

```
share URL
   │
   ├─► scraper            platform-specific; normalizes to a common chat JSON schema
   │                      chatgpt: curl_cffi + payload embedded in a page <script>
   │                      gemini : Playwright (JS-rendered page) + BeautifulSoup
   │                      claude : public chat_snapshots API
   │
   ├─► create_chunks()    pairs user+assistant turns into ≤1000-char chunks,
   │                      strips markdown/emoji into a clean `embedded_text`
   │
   ├─► create_embeddings()  sentence-transformers/all-MiniLM-L6-v2 (normalized)
   │                        also embeds the 4 fixed section queries → docs_embed.json
   │
   ├─► add_chunks_to_chroma()  persistent Chroma collection `conv-<conversation_id>`
   │                           (cosine space)
   │
   ├─► retrieve_data()    per section: semantic top-15 + BM25 top-15,
   │                      min-max normalized, blended 0.65 semantic / 0.35 keyword,
   │                      top 3 kept
   │
   ├─► openai_llm()       Groq (OpenAI-compatible endpoint), model openai/gpt-oss-120b.
   │                      Heavily constrained anti-hallucination prompt; returns JSON with
   │                      overview / key_decisions / problems_solutions / technical_details
   │
   └─► generate_pdf()     ReportLab → app/output/memory_export.pdf, returned as a download
```

The PDF opens with instructions addressed to the *receiving* agent, then a details table
(title, source URL, platform, timestamp), then the four sections.

---

## Layout

```
app/
  main.py                        FastAPI app, mounts the router
  routers/conversation.py        POST /submit-link — the whole pipeline, end to end
  services/
    chatgpt_scraper/chatgptscraper.py   load_chatgpt_chat(url)
    gemini_scraper/geminiscraper.py     load_gemini_chat(url)
    claude_scraper/claudescraper.py     load_claude_chat(url)
    chunks.py                    create_chunks(chat_data)
    embedding.py                 create_embeddings(chunks), get_docs_embed()
    chroma.py                    add_chunks_to_chroma(embedded_chunks)
    retrieval.py                 retrieve_data(conversation_id)  — hybrid search
    llm.py                       openai_llm(retrieved_data)      — section writer
    pdfgenerator.py              generate_pdf(...)
  demo_data/<platform>/<n>/      captured intermediates per pipeline stage (committed)
  chroma_data/                   persistent vector store (gitignored)
  output/                        generated PDFs
```

`demo_data/` holds real captured output from each stage (`scrape.html`, `chat_data.json`,
`chunks.json`, `embed.json`, `retrieved_data.json`, `final_data.json`). It doubles as
fixtures — most services have a commented-out `with open(...)` block at the top so you can
run one stage standalone against a saved file instead of re-scraping.

---

## Chat JSON schema

Every scraper normalizes to this shape; everything downstream depends on it:

```json
{
  "conversation_id": "…",
  "platform": "gemini",
  "source_url": "https://…",
  "title": "…",
  "scraped_at": "2026-09-16T…+00:00",
  "messages": [
    {
      "id": "f8a4cb4a-…",
      "role": "user",
      "content": [{ "type": "text", "text": "hello chat how are you" }],
      "timestamp": 1789036843.168569
    }
  ]
}
```

Scrapers return `{"ok": True, "data": <schema>}` on success and
`{"ok": False, "message": "<stage>: <what failed>"}` on failure. Internal helpers use a
narrower `_ok(value)` / `_fail(message)` pair that wraps the payload under `"value"`.

---

## Setup

Requires Python 3.11+ and roughly 2–3 GB of disk for `torch` and the embedding model.

```bash
python -m venv venv
venv\Scripts\activate            # Windows;  source venv/bin/activate on macOS/Linux

# requirements.txt is UTF-16 encoded (written by PowerShell redirection).
# If pip chokes on it, re-encode first:
#   python -c "open('requirements.txt','w',encoding='utf-8').write(open('requirements.txt',encoding='utf-16').read())"
pip install -r requirements.txt

playwright install chromium      # needed by the Gemini scraper
```

Create a `.env` in the repo root:

```
XAI_API_KEY=<groq api key>        # used by llm.py against api.groq.com
GEMINI_API_KEY=<google api key>   # only for the commented-out gemini_llm() path
```

`XAI_API_KEY` is a name kept for historical reasons — it is passed as the API key to the
**Groq** OpenAI-compatible endpoint, not to xAI.

On first run `sentence-transformers` downloads `all-MiniLM-L6-v2` (~90 MB) and caches it.

---

## Running

```bash
uvicorn app.main:app --reload
```

`POST /submit-link` takes `url` as a **query parameter** (it is a bare `str` argument, so
FastAPI does not read it from the body) and responds with the PDF:

```bash
curl -X POST "http://127.0.0.1:8000/submit-link?url=https://claude.ai/share/<id>" \
     --output memory_export.pdf
```

Platform is chosen by substring match on the URL — `chatgpt`, `gemini`, or `claude`.
Anything else returns `"platform could not identified"`.

Interactive docs: http://127.0.0.1:8000/docs

---

## Tuning

| Where | Knob | Default |
|---|---|---|
| `services/chunks.py` | `max_char`, `overlap` | 1000, 100 |
| `services/embedding.py` | embedding model | `all-MiniLM-L6-v2` |
| `services/embedding.py` | the four section queries | `queries` dict in `get_docs_embed()` |
| `services/retrieval.py` | `TOP_SEMANTIC`, `TOP_KEYWORD`, `FINAL_TOP_K` | 15, 15, 3 |
| `services/retrieval.py` | `SEMANTIC_WEIGHT`, `KEYWORD_WEIGHT` | 0.65, 0.35 |
| `services/llm.py` | model / endpoint | `openai/gpt-oss-120b` on Groq |

Adding a section means adding a query to `get_docs_embed()`, a matching section rule in the
`llm.py` prompt plus its key in the output JSON, and an entry in `sections` in
`pdfgenerator.py`. All of those must stay in sync.

There is a commented-out `CrossEncoder("BAAI/bge-reranker-base")` in `retrieval.py` — a
reranking stage that was scaffolded but never wired into `retrieve_section()`.

---

## Known rough edges

These are real and will bite; they are listed so nobody rediscovers them the hard way.

- **The Claude path crashes in the router.** `load_claude_chat()` returns `_ok(formatted_data)`
  (`{"ok": True, "value": …}`), but `submit_link` reads `response.get("data")`. That yields
  `None`, and the next line raises `AttributeError`. ChatGPT and Gemini return `"data"`
  correctly. Fix by returning `{"ok": True, "data": formatted_data}`.
- **Hardcoded demo paths.** `chunks.py`, `embedding.py`, `retrieval.py` and `llm.py` each
  have a module-level `platform = "gemini"` / `folder = "1"` and write their intermediates
  into `demo_data/gemini/1/`, *regardless of the platform actually being processed*.
  `retrieval.py` then reads `docs_embed.json` back from that same fixed path. So any run
  overwrites the gemini fixtures, and two concurrent requests will clobber each other.
  These paths need to become per-request (keyed by `conversation_id`, say) before this can
  serve more than one user at a time.
- **Chroma collections are never cleaned up.** Re-submitting the same conversation calls
  `collection.add` with chunk IDs that already exist in that collection.
- **No validation on the incoming URL**, and no auth on the endpoint.
- **`llm.py` does `json.loads(response.output_text)`** with no guard — a non-JSON model
  response raises instead of degrading.
- **The scrapers depend on undocumented page internals** (ChatGPT's `streamController.enqueue`
  payload, Gemini's `<share-turn-viewer>` DOM, Claude's `chat_snapshots` endpoint). Expect
  them to break when those change; each returns a descriptive `_fail` message naming the
  stage that broke.
- **Only text survives the pipeline.** Non-text content blocks are skipped in the Claude
  scraper, and `create_chunks` reads `content[0]["text"]` only. `demo_data/non-text/` holds
  a capture of a conversation where this matters.
