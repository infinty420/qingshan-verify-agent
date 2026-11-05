"""Markdown 制度文档分块：按标题层级切分，保留章节路径；超长段落按句子二次切分。"""
import re

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
MAX_LEN = 500


def chunk_markdown(text: str, max_len: int = MAX_LEN) -> list[dict]:
    blocks: list[tuple[str, str]] = []
    path: list[str] = []
    buf: list[str] = []

    def flush():
        content = "\n".join(buf).strip()
        if content:
            blocks.append((" > ".join(path), content))
        buf.clear()

    for line in text.splitlines():
        m = HEADING_RE.match(line.strip())
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            path = path[: level - 1]
            path.append(title)
            buf.append(title)
        else:
            buf.append(line)
    flush()

    chunks: list[dict] = []
    for section, content in blocks:
        if len(content) <= max_len:
            chunks.append({"section": section or "正文", "content": content})
            continue
        parts, cur = [], ""
        for seg in re.split(r"(?<=[。！？；\n])", content):
            if cur and len(cur) + len(seg) > max_len:
                parts.append(cur)
                cur = seg
            else:
                cur += seg
        if cur:
            parts.append(cur)
        for p in parts:
            p = p.strip()
            if p:
                chunks.append({"section": section or "正文", "content": p})
    return chunks
