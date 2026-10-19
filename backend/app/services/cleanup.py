import shutil
from pathlib import Path

from app.services.chroma import chromapath, collection_name, get_client


app_dir = Path(__file__).parent.parent
assets_root = app_dir / "storage" / "assets"
output_dir = app_dir / "output"


def drop_vectors(conversation_id):
    try:
        get_client().delete_collection(collection_name(conversation_id))
    except Exception:
        pass


def drop_assets(conversation_id):
    if not conversation_id or not assets_root.is_dir():
        return

    for platform_dir in assets_root.iterdir():
        if not platform_dir.is_dir():
            continue

        target = (platform_dir / str(conversation_id)).resolve()

        if target.parent == platform_dir.resolve() and target.is_dir():
            shutil.rmtree(target, ignore_errors=True)


def discard_conversation(conversation_id):
    drop_vectors(conversation_id)
    drop_assets(conversation_id)


def sweep_orphans():
    # Sessions live in memory, so anything left on disk from a previous
    # process can never be reached again.
    shutil.rmtree(chromapath, ignore_errors=True)
    shutil.rmtree(assets_root, ignore_errors=True)

    for leftover in output_dir.glob("memory_export-*.pdf"):
        leftover.unlink(missing_ok=True)
