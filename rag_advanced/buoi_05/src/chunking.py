# -*- coding: utf-8 -*-
"""chunking.py — Ba chiến lược chunking: fixed-size, semantic, hierarchical.

Mỗi chunk có: chunk_id, strategy, source, page_start, page_end, text, structure.

- fixed_size: cắt theo số ký tự cố định, có overlap.
- semantic: ưu tiên ranh giới đoạn văn (dòng trống / kết đoạn / cách dòng),
  không cắt giữa câu khi có thể.
- hierarchical: mỗi mốc cấu trúc (Chương -> Mục -> Điều/Khoản -> Điểm) là
  mốc bắt đầu của 1 chunk. KHÔNG bịa cấu trúc: nếu không tìm thấy mốc nào sẽ
  ghi cảnh báo và fallback sang semantic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from src.ocr import PageText

SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")
PARAGRAPH_RE = re.compile(r"\n{2,}")
LINE_RE = re.compile(r"\n+")


@dataclass
class Chunk:
    chunk_id: str
    strategy: str
    source: str
    page_start: int
    page_end: int
    text: str
    structure: Optional[dict] = None


# ---------------------------------------------------------------- helpers
def _global_text_and_pagemap(pages: list[PageText]) -> tuple[str, list[int]]:
    """Ghép text các trang thành 1 chuỗi + bản đồ char_index -> số trang."""
    full = ""
    pagemap: list[int] = []
    for pt in pages:
        start = len(full)
        full += pt.text
        pagemap.extend([pt.page] * (len(full) - start))
        if pt is not pages[-1]:
            full += "\n"
            pagemap.append(pt.page)
    return full, pagemap


def _page_range(pagemap: list[int], a: int, b: int) -> tuple[int, int]:
    if b - 1 >= len(pagemap):
        b = len(pagemap)
    if a >= len(pagemap):
        return pagemap[-1], pagemap[-1]
    return pagemap[a], pagemap[b - 1]


def _split_sentences(text: str) -> list[str]:
    """Tách theo dấu câu, giữ nguyên ký tự (không cắt giữa câu)."""
    parts = SENTENCE_END_RE.split(text.strip())
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------- fixed-size
def chunk_fixed_size(
    pages: list[PageText],
    source: str,
    size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    full, pagemap = _global_text_and_pagemap(pages)
    chunks: list[Chunk] = []
    if not full.strip():
        return chunks
    start = 0
    n = len(full)
    idx = 0
    while start < n:
        end = min(start + size, n)
        chunk = full[start:end]
        if chunk.strip():
            p_s, p_e = _page_range(pagemap, start, end - 1)
            chunks.append(
                Chunk(
                    chunk_id=f"fs-{idx:04d}",
                    strategy="fixed_size",
                    source=source,
                    page_start=p_s,
                    page_end=p_e,
                    text=chunk,
                    structure={"size": size, "overlap": overlap},
                )
            )
            idx += 1
        if end >= n:
            break
        start = max(start + size - overlap, start + 1)
    return chunks


# ---------------------------------------------------------------- semantic
def chunk_semantic(
    pages: list[PageText],
    source: str,
    target_size: int = 600,
    max_size: int = 1200,
) -> list[Chunk]:
    """Chunk theo đoạn văn; chỉ cắt cứng khi 1 đoạn quá lớn, ưu tiên hết câu."""
    full, pagemap = _global_text_and_pagemap(pages)
    chunks: list[Chunk] = []
    if not full.strip():
        return chunks

    paragraphs = PARAGRAPH_RE.split(full)

    def _push(text: str, start_char: int) -> None:
        end_char = start_char + len(text)
        p_s, p_e = _page_range(pagemap, start_char, end_char - 1)
        chunks.append(
            Chunk(
                chunk_id=f"sem-{len(chunks):04d}",
                strategy="semantic",
                source=source,
                page_start=p_s,
                page_end=p_e,
                text=text.strip(),
                structure={"type": "paragraph-group"},
            )
        )

    cursor = 0
    buffer = ""
    buffer_start = 0
    for para in paragraphs:
        if len(para) > max_size:
            if buffer.strip():
                _push(buffer, buffer_start)
                buffer, buffer_start = "", 0
            # chia đoạn lớn theo câu, gom theo max_size
            sentences = _split_sentences(para)
            group = ""
            gstart = cursor
            for sent in sentences:
                if group and len(group) + len(sent) + 1 > target_size:
                    _push(group, gstart)
                    gstart = cursor + len(group) + 1
                    group = ""
                group = (group + " " + sent).strip() if group else sent
                cursor = gstart + len(group)
            if group.strip():
                _push(group, gstart)
            cursor = gstart + len(group)
            continue

        if buffer and len(buffer) + len(para) + 2 > target_size:
            _push(buffer, buffer_start)
            buffer, buffer_start = "", 0
        if not buffer:
            buffer_start = cursor
        buffer = (buffer + "\n\n" + para).strip() if buffer else para.strip()
        cursor = buffer_start + len(buffer)

    if buffer.strip():
        _push(buffer, buffer_start)

    return chunks


# ---------------------------------------------------------------- hierarchical
# Mốc cấu trúc tiếng Việt + heading markdown từ Llamaparse.
_STRUCTURE_PATTERNS = [
    # (regex, loại cấu trúc, mức ưu tiên)
    (re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE), "heading", 0),
    (re.compile(r"^\s*Chương\s+[IVXLCDM0-9]+\b.*$", re.MULTILINE), "Chương", 1),
    (re.compile(r"^\s*Mục\s+[0-9IVX]+\b.*$", re.MULTILINE), "Mục", 2),
    (re.compile(r"^\s*Điều\s+\d+[a-z]?\s*[.:]?.*$", re.MULTILINE), "Điều", 3),
    (re.compile(r"^\s*Khoản\s+\d+[a-z]?\s*[.:]?.*$", re.MULTILINE), "Khoản", 4),
    (re.compile(r"^\s*[0-9]{1,2}[.)]\s+\S.*$", re.MULTILINE), "Điểm", 5),
]


def _find_structure_markers(full: str) -> list[tuple[int, int, dict]]:
    """Trả về danh sách (start, end, structure) các mốc cấu trúc tìm thấy."""
    markers: list[tuple[int, int, dict, int]] = []  # (start, end, struct, prio)
    for pat, kind, prio in _STRUCTURE_PATTERNS:
        for m in pat.finditer(full):
            if kind == "heading":
                level = len(m.group(1))
                title = m.group(2).strip()
                struct = {"type": kind, "title": title, "level": level}
            elif kind == "Điểm":
                title = m.group(0).strip()
                struct = {"type": kind, "title": title, "level": prio}
            else:
                title = m.group(0).strip()
                struct = {"type": kind, "title": title, "level": prio}
            markers.append((m.start(), m.end(), struct, prio))
    markers.sort(key=lambda x: x[0])
    # loại bỏ các mốc lồng nhau trùng vị trí (giữ mốc cụ thể hơn / mức nhỏ hơn)
    kept: list[tuple[int, int, dict]] = []
    last_end = -1
    for start, end, struct, prio in markers:
        if start < last_end:
            continue
        kept.append((start, end, struct))
        last_end = end
    return kept


def chunk_hierarchical(
    pages: list[PageText],
    source: str,
    max_size: int = 3000,
) -> tuple[list[Chunk], list[str]]:
    full, pagemap = _global_text_and_pagemap(pages)
    warnings: list[str] = []
    if not full.strip():
        return [], warnings

    markers = _find_structure_markers(full)
    if not markers:
        warnings.append(
            "KHÔNG phát hiện cấu trúc (Chương/Mục/Điều/heading) trong văn bản — "
            "hierarchical fallback sang semantic. Không bịa heading."
        )
        return chunk_semantic(pages, source), warnings

    chunks: list[Chunk] = []
    segments: list[tuple[int, int, Optional[dict]]] = []
    if markers and markers[0][0] > 0:
        segments.append((0, markers[0][0], None))  # phần mở đầu trước mốc đầu tiên
    for i, (s, _e, struct) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(full)
        segments.append((s, end, struct))
    for a, b, struct in segments:
        text = full[a:b].strip()
        if not text:
            continue
        if len(text) > max_size:
            warnings.append(
                f"Chunk hierarchical '{struct['title'] if struct else '?'}' dài {len(text)} ký tự "
                f"(> {max_size}) — giữ nguyên để không phá vỡ cấu trúc."
            )
        p_s, p_e = _page_range(pagemap, a, b - 1)
        chunks.append(
            Chunk(
                chunk_id=f"hier-{len(chunks):04d}",
                strategy="hierarchical",
                source=source,
                page_start=p_s,
                page_end=p_e,
                text=text,
                structure=struct,
            )
        )
    return chunks, warnings


# ---------------------------------------------------------------- dispatcher
def chunk_all(
    pages: list[PageText],
    source: str,
    fixed_size: int = 500,
    fixed_overlap: int = 50,
) -> dict[str, list[Chunk]]:
    results: dict[str, list[Chunk]] = {}
    results["fixed_size"] = chunk_fixed_size(
        pages, source, size=fixed_size, overlap=fixed_overlap
    )
    results["semantic"] = chunk_semantic(pages, source)
    hier, _warn = chunk_hierarchical(pages, source)
    results["hierarchical"] = hier
    return results


# ---------------------------------------------------------------- stats
def chunk_stats(chunks: list[Chunk]) -> dict:
    lengths = [len(c.text) for c in chunks]
    if not lengths:
        return {"count": 0, "min": 0, "max": 0, "avg": 0.0}
    return {
        "count": len(chunks),
        "min": min(lengths),
        "max": max(lengths),
        "avg": round(sum(lengths) / len(lengths), 1),
    }
