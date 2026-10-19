// Talks to the FastAPI backend in backend/app/routers/conversation.py.
// The pipeline is split into four small requests (scrape -> analyze -> write
// -> export) so the UI can show real progress instead of one long spinner.

const BASE = 'http://127.0.0.1:8000'

async function postJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const problem = await res.json().catch(() => null)
    throw new Error(problem?.detail || `${path} failed (${res.status})`)
  }

  return res.json()
}

export function scrapeConversation(url) {
  return postJSON('/scrape', { url })
}

export function analyzeConversation(conversationId) {
  return postJSON('/analyze', { conversation_id: conversationId })
}

export function writeDocument(conversationId) {
  return postJSON('/write', { conversation_id: conversationId })
}

export async function exportPdf(conversationId) {
  const res = await fetch(`${BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId }),
  })

  if (!res.ok) {
    const problem = await res.json().catch(() => null)
    throw new Error(problem?.detail || `export failed (${res.status})`)
  }

  const blob = await res.blob()
  const filenameMatch = (res.headers.get('Content-Disposition') || '').match(/filename="?([^"]+)"?/)

  return {
    blob,
    filename: filenameMatch ? filenameMatch[1] : 'memory_export.pdf',
    codeBlocks: Number(res.headers.get('X-Code-Blocks') || 0),
    imagesEmbedded: Number(res.headers.get('X-Images-Embedded') || 0),
    filesMissing: Number(res.headers.get('X-Files-Missing') || 0),
  }
}

/**
 * Runs the whole scrape -> analyze -> write -> export pipeline for one share
 * link, calling onStage(index) right before each of the four steps starts.
 */
export async function convertConversation(url, onStage) {
  onStage?.(0)
  const { conversation_id: conversationId, platform } = await scrapeConversation(url)

  onStage?.(1)
  await analyzeConversation(conversationId)

  onStage?.(2)
  await writeDocument(conversationId)

  onStage?.(3)
  const result = await exportPdf(conversationId)

  return { ...result, platform }
}
