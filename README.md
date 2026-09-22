# AI Chat Exporter — Agent Memory Transfer

A web app that turns a **shared AI chat link** (ChatGPT, Gemini, or Claude) into a
**"memory transfer" PDF** — a structured document another AI agent can read to pick up the
conversation where the previous one left off.

You paste a share URL into the landing page. The backend scrapes the conversation, runs it
through a retrieval pipeline (chunk → embed → vector store → hybrid search), asks an LLM to
reorganize the retrieved material into four fixed sections, and renders the result as a PDF —
with the conversation's images and code blocks carried over verbatim.

The project is split into two apps:

```
backend/    FastAPI service — the pipeline described below
frontend/   React + Vite landing page and submit UI
```

---

## Pipeline

The pipeline is exposed as four small REST calls instead of one long request, so the frontend
can show real per-stage progress. State for an in-flight conversation is held in an in-memory
session between calls (see [Backend layout](#backend-layout)).

```
share URL
   │
   ├─► POST /api/scrape     platform-specific scraper; normalizes to a common chat JSON schema
   │                        chatgpt: curl_cffi + payload embedded in a page <script>
   │                        gemini : Playwright (JS-rendered page) + BeautifulSoup
   │                        claude : public chat_snapshots API
   │
   │                        also on this call:
   │                        - assets.manifest()       collects & classifies image/file attachments
   │                        - codeblocks.extract_code_blocks()  pulls fenced code + ASCII diagrams
   │                        - create_chunks()          pairs user+assistant turns into ≤1000-char
   │                                                    chunks, strips markdown/emoji into a clean
   │                                                    `embedded_text`
   │                        → session saved, keyed by conversation_id
   │
   ├─► POST /api/analyze    create_embeddings()   sentence-transformers/all-MiniLM-L6-v2
   │                        (normalized) — also embeds the 4 fixed section queries
   │                        add_chunks_to_chroma() persistent Chroma collection per conversation
   │                        retrieve_data()        per section: semantic top-15 + BM25 top-15,
   │                                                min-max normalized, blended 0.65 semantic /
   │                                                0.35 keyword, top 5 kept
   │
   ├─► POST /api/write      openai_llm()  Groq (OpenAI-compatible endpoint), openai/gpt-oss-120b.
   │                        Heavily constrained anti-hallucination prompt, token-budgeted so the
   │                        request fits the key's rate limit; returns JSON with
   │                        overview / key_decisions / problems_solutions / technical_details
   │
   └─► POST /api/export     generate_pdf()  ReportLab → PDF, streamed back and deleted after
                             the response finishes. Session is dropped once this returns.
```

The PDF opens with instructions addressed to the *receiving* agent, then a details table
(title, source URL, platform, timestamp), the four written sections, and finally the
conversation's embedded images and code blocks/diagrams, kept verbatim rather than summarized.

---

## Backend layout

```
backend/
  requirements.txt
  .env                            not committed — see Setup
  app/
    main.py                       FastAPI app, CORS, mounts the router
    routers/conversation.py       /api/scrape, /api/analyze, /api/write, /api/export
    services/
      chatgpt_scraper/chatgptscraper.py   load_chatgpt_chat(url)
      gemini_scraper/geminiscraper.py     load_gemini_chat(url)
      claude_scraper/claudescraper.py     load_claude_chat(url)
      session_store.py             in-memory per-conversation state between the 4 requests
                                    (TTL-evicted; swap for Redis/DB to run more than one worker)
      assets.py                    classifies/collects message attachments (images embeddable,
                                    others reference-only), builds the embedded/missing manifest
      codeblocks.py                extracts fenced code blocks and ASCII-art/box-drawing diagrams
                                    from message text, deduped by content fingerprint
      chunks.py                    create_chunks(chat_data)
      embedding.py                 create_embeddings(chunks), get_docs_embed()
      chroma.py                    add_chunks_to_chroma(embedded_chunks)
      retrieval.py                 retrieve_data(conversation_id, docs_embed) — hybrid search
      llm.py                       openai_llm(retrieved_data) — section writer, budget-aware
      pdfgenerator.py              generate_pdf(...) — text sections + images + code blocks
    chroma_data/                   persistent vector store (gitignored)
    output/                        generated PDFs (gitignored, deleted after each response)
```

Scrapers return `{"ok": True, "data": <schema>}` on success and
`{"ok": False, "message": "<stage>: <what failed>"}` on failure.

### Chat JSON schema

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

Non-text content entries (images, files) carry a `file_id` instead of `text` and are picked up
by `assets.py` rather than `chunks.py`.

---

## Frontend layout

```
frontend/
  src/
    api.js                        talks to /api/*; convertConversation() drives all 4 stages
                                   and reports progress via an onStage(index) callback
    App.jsx                       page composition
    components/
      Nav.jsx, CaveHero.jsx       landing hero
      SubmitBox.jsx               the actual product entry point — paste a link, watch the
                                   4 pipeline stages, download the PDF
      BrandMarquee.jsx, ProblemSolution.jsx, SupportedAgents.jsx, FAQ.jsx, Footer.jsx
      HowItWorks/                 animated step-by-step explainer (GSAP-driven orbit/arrows)
  vite.config.js                  dev server proxies /api/* to http://127.0.0.1:8000
```

Built with React 19, Vite, Framer Motion and GSAP for the landing animations.

---

## Setup

Requires Python 3.11+ (~2–3 GB disk for `torch` and the embedding model), Node 18+, and a Groq
API key.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows;  source venv/bin/activate on macOS/Linux

pip install -r requirements.txt
playwright install chromium      # needed by the Gemini scraper
```

Create `backend/.env`:

```
GROQ_API_KEY=<groq api key>       # used by app/services/llm.py against api.groq.com
ALLOWED_ORIGINS=http://localhost:5173   # comma-separated; defaults to * if unset
```

`XAI_API_KEY` is still accepted as a fallback name for `GROQ_API_KEY` for backward
compatibility, but it is passed to **Groq**, not to xAI.

On first run `sentence-transformers` downloads `all-MiniLM-L6-v2` (~90 MB) and caches it.

### Frontend

```bash
cd frontend
npm install
```

---

## Running

```bash
# backend, from backend/
uvicorn app.main:app --reload      # http://127.0.0.1:8000, docs at /docs

# frontend, from frontend/
npm run dev                        # http://localhost:5173, proxies /api to the backend
```

Open the frontend, paste a share URL into the submit box, and watch it run through the four
stages. Or drive the API directly:

```bash
curl -X POST http://127.0.0.1:8000/api/scrape   -H "Content-Type: application/json" -d '{"url":"https://claude.ai/share/<id>"}'
curl -X POST http://127.0.0.1:8000/api/analyze  -H "Content-Type: application/json" -d '{"conversation_id":"<id>"}'
curl -X POST http://127.0.0.1:8000/api/write    -H "Content-Type: application/json" -d '{"conversation_id":"<id>"}'
curl -X POST http://127.0.0.1:8000/api/export   -H "Content-Type: application/json" -d '{"conversation_id":"<id>"}' --output memory_export.pdf
```

Platform is chosen by an allowlist of hosts (`chatgpt.com`/`chat.openai.com`,
`gemini.google.com`/`g.co`, `claude.ai`) in `routers/conversation.py`. Anything else is
rejected with a 422 before any scraping happens.

---

## Tuning

| Where | Knob | Default |
|---|---|---|
| `services/chunks.py` | `MAX_CHARS`, `OVERLAP` | 1000, 100 |
| `services/embedding.py` | embedding model | `all-MiniLM-L6-v2` |
| `services/embedding.py` | the four section queries | `SECTION_QUERIES` |
| `services/retrieval.py` | `TOP_SEMANTIC`, `TOP_KEYWORD`, `FINAL_TOP_K` | 15, 15, 5 |
| `services/retrieval.py` | `SEMANTIC_WEIGHT`, `KEYWORD_WEIGHT` | 0.65, 0.35 |
| `services/llm.py` | model / endpoint | `openai/gpt-oss-120b` on Groq |
| `services/llm.py` | `CONTEXT_TOKEN_LIMIT`, `MAX_OUTPUT_TOKENS` | 8000, 2500 |
| `services/assets.py` | `MAX_EMBED_BYTES` | 5 MB |
| `session_store.py` | `TTL_SECONDS` | 30 min |

Adding a section means adding a query to `SECTION_QUERIES` in `embedding.py`, a matching
section rule in the `llm.py` prompt plus its key in `SECTION_KEYS`, and an entry for it in
`pdfgenerator.py`. All of those must stay in sync.

There is a commented-out `CrossEncoder("BAAI/bge-reranker-base")` in `retrieval.py` — a
reranking stage that was scaffolded but never wired into `retrieve_section()`.

---

## Known rough edges

- **In-memory session store is single-process.** `session_store.py` is a process-local dict.
  Fine for a single dev/demo `uvicorn` worker; running multiple workers (or a serverless
  deployment) needs it swapped for Redis or a DB, since a request can land on a worker that
  never saw the earlier stage.
- **Chroma collections are never cleaned up.** Re-submitting the same conversation calls
  `collection.add` with chunk IDs that already exist in that collection.
- **No auth on the endpoints**, and no rate limiting beyond what Groq itself enforces.
- **The scrapers depend on undocumented page internals** (ChatGPT's `streamController.enqueue`
  payload, Gemini's `<share-turn-viewer>` DOM, Claude's `chat_snapshots` endpoint). Expect
  them to break when those change; each returns a descriptive `_fail` message naming the
  stage that broke.
- **`requirements.txt` may save as UTF-16** if regenerated with `pip freeze > requirements.txt`
  from PowerShell. If `pip install -r requirements.txt` chokes on it, re-encode first:
  `python -c "open('requirements.txt','w',encoding='utf-8').write(open('requirements.txt',encoding='utf-16').read())"`.
