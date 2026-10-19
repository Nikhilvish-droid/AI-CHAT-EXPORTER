import time

from app.services.cleanup import discard_conversation

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
        discard_conversation(conversation_id)


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
    discard_conversation(conversation_id)
