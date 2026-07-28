"""
Object storage abstraction.

POC scope: local filesystem under ./data/objects. The interface
(`put_object`/`get_object`) is what the rest of the codebase depends on,
so swapping to S3/S3-compatible storage (per blueprint §9) later is a
one-file change — nothing above this layer needs to know.
"""
import os
import uuid

_STORAGE_ROOT = os.path.join(os.getcwd(), "data", "objects")
os.makedirs(_STORAGE_ROOT, exist_ok=True)


def put_object(file_bytes: bytes, extension: str) -> str:
    """Stores bytes, returns an object_key that get_object can resolve later."""
    key = f"{uuid.uuid4()}.{extension.lstrip('.')}"
    path = os.path.join(_STORAGE_ROOT, key)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return key


def get_object(object_key: str) -> bytes:
    with open(get_object_path(object_key), "rb") as f:
        return f.read()


def get_object_path(object_key: str) -> str:
    """Resolves an object_key to a local file path. LangChain's document
    loaders (PyPDFLoader, TextLoader) read from disk paths, not raw bytes,
    so ingestion uses this instead of get_object()."""
    return os.path.join(_STORAGE_ROOT, object_key)
