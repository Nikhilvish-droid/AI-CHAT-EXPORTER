"""Holds pipeline state between the /api/* requests for one conversation.

The pipeline is split into a few small requests (scrape -> analyze -> write ->
export) so the frontend can show progress per stage instead of one long call.
HTTP requests don't share memory, so this dict is what carries each
conversation's data from one request to the next. It's process-local - fine
for a single dev/demo server; swap for Redis or a DB if this ever runs
multiple workers.

Entries older than TTL_SECONDS are dropped the next time save() runs, so a
conversion someone abandoned mid-flow (closed the tab after /scrape) doesn't
sit in memory forever.
"""

import time

TTL_SECONDS = 30 * 60

_sessions = {}


def _evict_expired(now):
    expired = [
        conversation_id
        for conversation_id, entry in _sessions.items()
        if now - entry["_saved_at"] > TTL_SECONDS
    ]

    for conversation_id in expired:
        del _sessions[conversation_id]


def save(conversation_id, **data):
    now = time.time()
    _evict_expired(now)

    session = _sessions.setdefault(conversation_id, {})
    session.update(data)
    session["_saved_at"] = now


def load(conversation_id):
    return _sessions.get(conversation_id)


def drop(conversation_id):
    _sessions.pop(conversation_id, None)
