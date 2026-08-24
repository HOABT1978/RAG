# -*- coding: utf-8 -*-
"""ocr.py — Trích xuất text từ PDF tiếng Việt (OCR fallback).

Luồng độc lập:
1. Thử lấy text layer bằng PyMuPDF (fitz) theo từng trang.
2. Đánh giá chất lượng từng trang: rỗng / quá ngắn / lỗi font-encoding
   (dấu tiếng Việt vỡ như "CQNG HOAXA") / ký tự lạ.
3. Nếu có trang lỗi -> render các trang ra ảnh PNG (output/pages/) để minh hoạ
   và gửi OCR TOÀN BỘ file bằng Llamaparse (llama-cloud).
4. Chuẩn hoá Unicode NFC.
5. Trả về danh sách PageText + metadata (source, page, ocr_used, language).
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# Bộ ký tự tiếng Việt có dấu dùng để phát hiện text layer bị vỡ encoding.
VIETNAMESE_DIACRITICS = set(
    "ăâđêôơư"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
    "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ĂÂĐÊÔƠƯ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊ"
    "ÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)
_LETTER_RE = re.compile(r"[A-Za-zÀ-ỹ]", re.UNICODE)
_PAGE_BREAK_RE = re.compile(r"<!--\s*PageBreak\s*-->")

MIN_TEXT_LETTERS = 30      # dưới mức này xem như trang quá ngắn để đánh giá
MIN_ACCEPTABLE_LETTERS = 25
MIN_DIACRITIC_DENSITY = 0.005  # text tiếng Việt tốt luôn có > 0.5% chữ có dấu


@dataclass
class PageText:
    page: int                          # số trang (1-based)
    text: str
    method: str                        # "pymupdf" | "llamaparse"
    image: Optional[str] = None        # đường dẫn ảnh render (nếu có)


@dataclass
class ExtractResult:
    source: str
    pages: list[PageText]
    ocr_used: bool
    warnings: list[str] = field(default_factory=list)
    language: str = "vi"
    raw_path: Optional[str] = None
    raw_meta_path: Optional[str] = None

    @property
    def full_text(self) -> str:
        return "\n".join(p.text for p in self.pages)


# ---------------------------------------------------------------- heuristic
def looks_corrupted(text: str) -> tuple[bool, str]:
    """Đánh giá 1 trang: text có bị lỗi / rỗng / ký tự lạ hay không.

    Trả về (có_lỗi, lý_do).
    """
    if not text or not text.strip():
        return True, "trang rỗng (không có text layer)"

    letters = _LETTER_RE.findall(text)
    if len(letters) < MIN_ACCEPTABLE_LETTERS:
        return True, f"text quá ngắn ({len(letters)} chữ cái)"

    if "\ufffd" in text:
        return True, "chứa ký tự thay thế U+FFFD (encoding hỏng)"

    vn = sum(1 for ch in letters if ch in VIETNAMESE_DIACRITICS)
    if len(letters) >= MIN_TEXT_LETTERS and vn / len(letters) < MIN_DIACRITIC_DENSITY:
        return True, f"encoding hỏng: chỉ {vn}/{len(letters)} chữ cái có dấu tiếng Việt"

    if sum(1 for ch in text if ch in "\x00\x01\x02\x03\x04\x05\x06\x07") > 0:
        return True, "chứa ký tự điều khiển"

    return False, "ok"


def normalize_nfc(text: str) -> str:
    """Chuẩn hoá Unicode NFC cho tiếng Việt."""
    return unicodedata.normalize("NFC", text)


# ---------------------------------------------------------------- pymupdf
def extract_with_pymupdf(pdf_path: str) -> list[str]:
    """Lấy text layer từng trang bằng PyMuPDF."""
    pages: list[str] = []
    with fitz.open(pdf_path) as doc:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            try:
                pages.append(normalize_nfc(page.get_text("text")))
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(f"pymupdf lỗi trang {i + 1}: {exc}") from exc
    return pages


# ---------------------------------------------------------------- llamaparse
def _split_markdown_pages(markdown_full: str) -> list[str]:
    parts = _PAGE_BREAK_RE.split(markdown_full or "")
    return [normalize_nfc(p.strip("\n")) for p in parts if p and p.strip()]


async def ocr_with_llamaparse(
    pdf_path: Path, api_key: str
) -> tuple[list[PageText], list[str]]:
    """Gửi toàn bộ PDF cho Llamaparse OCR. Trả về (pages, warnings).

    - Lần 1: parsing.parse(expand=["markdown_full"]) — đúng mẫu gọi trong bài học.
    - Lần 2: parsing.get(job_id, expand=["markdown"]) — lấy markdown theo từng
      trang (page_number) để có metadata page_start/page_end, không phải re-parse.
    """
    from llama_cloud import AsyncLlamaCloud

    warnings: list[str] = []
    client = AsyncLlamaCloud(api_key=api_key)
    file_obj = await client.files.create(file=str(pdf_path), purpose="parse")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full"],
    )

    job = getattr(result, "job", None)
    job_id = getattr(job, "id", None) if job is not None else None

    pages: list[PageText] = []

    # Lấy markdown theo từng trang để có page_number chính xác
    if job_id:
        try:
            per_page = await client.parsing.get(job_id=job_id, expand=["markdown"])
            pages_obj = getattr(getattr(per_page, "markdown", None), "pages", None)
            if pages_obj:
                for p in pages_obj:
                    if getattr(p, "success", False):
                        pages.append(
                            PageText(
                                page=int(getattr(p, "page_number", 0) or 0),
                                text=normalize_nfc(p.markdown),
                                method="llamaparse",
                            )
                        )
                    else:
                        warnings.append(
                            f"Trang {getattr(p, 'page_number', '?')} OCR thất bại: "
                            f"{getattr(p, 'error', 'lỗi không rõ')}"
                        )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Không lấy được markdown theo trang: {exc}")

    # Fallback: tách markdown_full theo mốc trang
    if not pages:
        md_full = getattr(result, "markdown_full", "") or ""
        raw_pages = _split_markdown_pages(md_full)
        for i, txt in enumerate(raw_pages, start=1):
            pages.append(PageText(page=i, text=txt, method="llamaparse"))
        if not raw_pages:
            warnings.append("Llamaparse không trả về trang nào (markdown_full rỗng).")

    return pages, warnings


def run_ocr_with_llamaparse(pdf_path: Path, api_key: str):
    """Bọc async để gọi từ code đồng bộ."""
    return asyncio.run(ocr_with_llamaparse(pdf_path, api_key))


# ---------------------------------------------------------------- render
def render_pages_to_images(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[str]:
    """Render từng trang PDF ra PNG (minh hoạ quá trình scan->OCR)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    images: list[str] = []
    with fitz.open(pdf_path) as doc:
        for i in range(doc.page_count):
            pix = doc.load_page(i).get_pixmap(dpi=dpi)
            target = out_dir / f"page_{i + 1:03d}.png"
            pix.save(target)
            images.append(str(target))
    return images


# ---------------------------------------------------------------- pipeline
def extract_document(
    pdf_path: Path,
    api_key: Optional[str],
    images_dir: Optional[Path] = None,
    always_ocr: bool = False,
) -> ExtractResult:
    """Trích xuất text cho 1 PDF: PyMuPDF trước, Llamaparse làm fallback."""
    warnings: list[str] = []
    source = pdf_path.name

    # Bước 1: thử text layer bằng PyMuPDF
    try:
        pymupdf_pages = extract_with_pymupdf(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"PyMuPDF không mở được PDF: {exc}")
        pymupdf_pages = []

    bad_pages: list[int] = []
    for i, txt in enumerate(pymupdf_pages, start=1):
        bad, reason = looks_corrupted(txt)
        if bad:
            bad_pages.append(i)
            warnings.append(f"Trang {i} không dùng được text layer: {reason}.")

    # Bước 2: nếu có trang lỗi -> render ảnh + OCR toàn bộ file
    ocr_used = False
    pages: list[PageText] = []
    if pymupdf_pages and not bad_pages and not always_ocr:
        # Dùng text layer, không cần OCR
        for i, txt in enumerate(pymupdf_pages, start=1):
            pages.append(PageText(page=i, text=txt, method="pymupdf"))
        warnings.append("Dùng text layer PyMuPDF — không cần gọi OCR.")
    else:
        if not pymupdf_pages:
            warnings.append("Không có text layer từ PyMuPDF — chuyển sang OCR.")
        elif bad_pages:
            warnings.append(
                f"{len(bad_pages)}/{len(pymupdf_pages)} trang lỗi — chuyển sang OCR toàn bộ file."
            )
        if images_dir is not None:
            try:
                render_pages_to_images(pdf_path, images_dir)
                warnings.append(f"Đã render {len(pymupdf_pages)} trang ra ảnh: {images_dir}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Không render được ảnh trang: {exc}")
        if not api_key:
            warnings.append("THIẾU LLAMA_CLOUD_API_KEY — bỏ qua OCR, giữ text thô.")
            for i, txt in enumerate(pymupdf_pages, start=1):
                pages.append(PageText(page=i, text=txt, method="pymupdf (raw)"))
        else:
            try:
                ocr_pages, ocr_warnings = run_ocr_with_llamaparse(pdf_path, api_key)
                warnings.extend(ocr_warnings)
                ocr_used = True
                pages.extend(ocr_pages)
                warnings.append("OCR Llamaparse hoàn tất.")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Llamaparse OCR thất bại: {exc} — giữ text thô PyMuPDF.")
                for i, txt in enumerate(pymupdf_pages, start=1):
                    pages.append(PageText(page=i, text=txt, method="pymupdf (raw)"))

    return ExtractResult(
        source=source,
        pages=pages,
        ocr_used=ocr_used,
        warnings=warnings,
    )
