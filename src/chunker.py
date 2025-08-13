import math

def chunk_text(text, max_chars=3000):
    """
    Simple chunker: groups paragraphs until near max_chars.
    Returns list of chunk strings.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    cur = []
    cur_len = 0
    for p in paragraphs:
        if cur_len + len(p) + 2 > max_chars and cur:
            chunks.append("\n\n".join(cur))
            cur = [p]
            cur_len = len(p)
        else:
            cur.append(p)
            cur_len += len(p) + 2
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks
