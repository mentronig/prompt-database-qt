import hashlib

def prompt_signature(title: str, content: str) -> str:
    t = (title or "").strip().lower()
    c = (content or "").strip().lower()
    m = hashlib.sha256()
    m.update(t.encode("utf-8"))
    m.update(b"\x1e")  # separator
    m.update(c.encode("utf-8"))
    return m.hexdigest()
