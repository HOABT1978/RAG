# -*- coding: utf-8 -*-
"""pipeline.py — CLI chạy luồng OCR + chunking cho Buổi 5.

Cách dùng:
    # Chỉ xem kế hoạch (không gọi OCR, không ghi file)
    python src/pipeline.py --dry-run

    # Chạy thật: OCR + chunking + ghi output/
    python src/pipeline.py --write

    # Xử lý 1 file, tinh chỉnh fixed-size
    python src/pipeline.py --write --pdf TT_39_2016_NHNN.pdf --size 400 --overlap 40

    # Chỉ chạy 1 chiến lược
    python src/pipeline.py --dry-run --strategy semantic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent  # buoi_05/
SRC = BASE / "src"
DATADEMO = BASE / "datademo"
OUTPUT = BASE / "output"
RAW_DIR = OUTPUT / "raw"
PAGES_DIR = OUTPUT / "pages"
CHUNK_DIR = OUTPUT / "chunks"

sys.path.insert(0, str(BASE))

from src.chunking import (  # noqa: E402
    Chunk,
    chunk_all,
    chunk_fixed_size,
    chunk_hierarchical,
    chunk_semantic,
    chunk_stats,
)
from src.ocr import (  # noqa: E402
    PageText,
    extract_document,
    looks_corrupted,
)


# ---------------------------------------------------------------- helpers
def _api_key_from_env() -> str | None:
    load_dotenv(SRC / ".env")
    return os.environ.get("LLAMA_CLOUD_API_KEY") or None


def _suffix(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower()


def _write_raw(extracted, raw_txt_path: Path, meta_path: Path) -> None:
    raw_txt_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for pt in extracted.pages:
        blocks.append(f"===== TRANG {pt.page} | nguồn: {pt.method} =====\n{pt.text}")
    raw_txt_path.write_text("\n\n".join(blocks), encoding="utf-8")
    meta = {
        "source": extracted.source,
        "language": extracted.language,
        "ocr_used": extracted.ocr_used,
        "method": "llamaparse" if extracted.ocr_used else "pymupdf",
        "pages": len(extracted.pages),
        "char_count": len(extracted.full_text),
        "warnings": extracted.warnings,
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _chunk_to_dict(c: Chunk) -> dict:
    return {
        "chunk_id": c.chunk_id,
        "strategy": c.strategy,
        "source": c.source,
        "page_start": c.page_start,
        "page_end": c.page_end,
        "text": c.text,
        "structure": c.structure,
    }


def _write_chunks(doc_stem: str, chunks_by_strategy: dict[str, list[Chunk]]) -> Path:
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    path = CHUNK_DIR / f"{doc_stem}_chunks.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for strategy, chunks in chunks_by_strategy.items():
            for c in chunks:
                fh.write(json.dumps(_chunk_to_dict(c), ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------- dry-run
def dry_run_one(pdf: Path, api_key_present: bool) -> dict:
    """Phân tích bằng PyMuPDF (không gọi OCR, không ghi file)."""
    from src.ocr import extract_with_pymupdf

    report: dict = {"file": pdf.name}
    try:
        pages = extract_with_pymupdf(str(pdf))
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"Không mở được PDF: {exc}"
        return report

    bad: list[int] = []
    for i, txt in enumerate(pages, start=1):
        bad_flag, reason = looks_corrupted(txt)
        if bad_flag:
            bad.append(i)
            report.setdefault("bad_reasons", {})[str(i)] = reason

    report["total_pages"] = len(pages)
    report["bad_pages"] = bad
    report["would_ocr"] = bool(bad) or not pages
    report["ocr_available"] = api_key_present
    if not report["would_ocr"]:
        report["plan"] = "Dùng text layer PyMuPDF (không gọi OCR)."

    # Ước lượng chunk bằng text layer (chỉ để xem trước)
    pt_pages = [
        PageText(page=i + 1, text=t, method="pymupdf")
        for i, t in enumerate(pages)
    ]
    for strat, chunks in chunk_all(pt_pages, pdf.name).items():
        report[f"chunk_{strat}"] = chunk_stats(chunks)
    return report


# ---------------------------------------------------------------- write
def process_one(pdf: Path, api_key: str | None, args) -> dict:
    stem = pdf.stem
    images_dir = PAGES_DIR / stem if args.render_pages else None
    extracted = extract_document(
        pdf, api_key=api_key, images_dir=images_dir, always_ocr=args.force_ocr
    )

    _write_raw(extracted, RAW_DIR / f"{stem}_raw.txt", RAW_DIR / f"{stem}_raw.json")

    chunks_by_strategy = chunk_all(
        extracted.pages,
        extracted.source,
        fixed_size=args.size,
        fixed_overlap=args.overlap,
    )
    chunks_path = _write_chunks(stem, chunks_by_strategy)

    # Cảnh báo hierarchical khi không có cấu trúc
    hier_warnings: list[str] = []
    _, hier_warn = chunk_hierarchical(extracted.pages, extracted.source)
    hier_warnings = hier_warn

    return {
        "file": pdf.name,
        "ocr_used": extracted.ocr_used,
        "pages": len(extracted.pages),
        "char_count": len(extracted.full_text),
        "warnings": extracted.warnings,
        "hierarchical_warnings": hier_warnings,
        "chunks_path": str(chunks_path),
        "stats": {k: chunk_stats(v) for k, v in chunks_by_strategy.items()},
    }


# ---------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Foundation Buổi 5 — OCR + chunking")
    parser.add_argument("--pdf", help="Tên file PDF trong datademo (mặc định: tất cả)")
    parser.add_argument("--strategy", choices=["all", "fixed_size", "semantic", "hierarchical"], default="all")
    parser.add_argument("--size", type=int, default=500, help="Kích thước chunk fixed-size (mặc định 500)")
    parser.add_argument("--overlap", type=int, default=50, help="Overlap fixed-size (mặc định 50)")
    parser.add_argument("--render-pages", action="store_true", default=True,
                        help="Render trang PDF ra ảnh minh hoạ (mặc định bật)")
    parser.add_argument("--force-ocr", action="store_true", help="Ép OCR toàn bộ dù text layer tốt")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Chỉ xem kế hoạch, không gọi OCR / không ghi file")
    mode.add_argument("--write", action="store_true", help="Chạy thật, ghi output/")
    args = parser.parse_args()

    api_key = _api_key_from_env()
    api_key_present = bool(api_key)

    if args.pdf:
        candidates = [DATADEMO / args.pdf]
    else:
        candidates = sorted(p for p in DATADEMO.iterdir() if _suffix(p.name) == "pdf")

    if not candidates:
        print("Không tìm thấy PDF nào trong datademo/.")
        sys.exit(1)

    print("=" * 70)
    print(f"MODE: {'DRY-RUN (không gọi OCR, không ghi file)' if args.dry_run else 'WRITE (chạy thật)'}")
    print(f"API key: {'CÓ trong src/.env' if api_key_present else 'KHÔNG có — OCR sẽ bị bỏ qua'}")
    print(f"PDFs: {', '.join(p.name for p in candidates)}")
    print("=" * 70)

    if args.dry_run:
        for pdf in candidates:
            rep = dry_run_one(pdf, api_key_present)
            print(f"\n--- {rep['file']} ---")
            for k, v in rep.items():
                print(f"  {k}: {v}")
            print("  (Chunk ước lượng dùng text layer PyMuPDF — chưa qua OCR)")
        print("\nBạn có thể chạy thật bằng lệnh:  python src/pipeline.py --write")
        return

    # WRITE mode
    OUTPUT.mkdir(parents=True, exist_ok=True)
    all_docs = []
    for pdf in candidates:
        try:
            rep = process_one(pdf, api_key, args)
            all_docs.append(rep)
            print(f"\n[OK] {pdf.name} — OCR={'CÓ' if rep['ocr_used'] else 'không'} — {rep['pages']} trang, {rep['char_count']} ký tự")
            for w in rep["warnings"]:
                print(f"     ! {w}")
            for s, st in rep["stats"].items():
                print(f"     [{s}] count={st['count']} min={st['min']} max={st['max']} avg={st['avg']}")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[LỖI] {pdf.name}: {exc} — bỏ qua, tiếp tục tài liệu khác.")

    # Báo cáo tổng hợp
    report_path = OUTPUT / "report.md"
    lines = [
        "# BÁO CÁO CHUNKING — BUỔI 5",
        "",
        f"Ngày: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Tài liệu | Chiến lược | Số chunk | Min | Max | Trung bình |",
        "|---|---|---|---|---|---|",
    ]
    for rep in all_docs:
        for s, st in rep["stats"].items():
            lines.append(
                f"| {rep['file']} | {s} | {st['count']} | {st['min']} | {st['max']} | {st['avg']} |"
            )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nĐã ghi báo cáo: {report_path}")


if __name__ == "__main__":
    main()
