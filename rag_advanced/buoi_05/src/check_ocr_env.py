# -*- coding: utf-8 -*-
"""check_ocr_env.py — Kiểm tra môi trường OCR (PASS/FAIL).

In bảng kết quả kiểm tra các công cụ cần thiết cho Buổi 5:
Python, PyMuPDF (fitz), Pillow, llama_cloud, Pydantic, Streamlit, python-dotenv.
Đồng thời kiểm tra thư mục datademo/ có PDF tiếng Việt hay không.

Cách chạy:
    python src/check_ocr_env.py
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATADEMO = BASE_DIR / "datademo"

REQUIRED_PACKAGES = [
    ("pymupdf", "PyMuPDF (đọc PDF)"),
    ("PIL", "Pillow (xử lý ảnh)"),
    ("llama_cloud", "llama-cloud (Llamaparse OCR)"),
    ("pydantic", "Pydantic (validate dữ liệu)"),
    ("streamlit", "Streamlit (UI)"),
    ("dotenv", "python-dotenv (đọc .env)"),
]


def check_python() -> tuple[bool, str]:
    version = sys.version.split()[0]
    major, minor, *_ = sys.version_info
    ok = major == 3 and minor >= 10
    msg = f"Python {version}"
    if not ok:
        msg += " (cần Python 3.10+)"
    return ok, msg


def check_package(module: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(module)
        return True, f"{module} {getattr(mod, '__version__', '?')}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{module} — LỖI: {type(exc).__name__}: {exc}"


def check_pdf_dir() -> tuple[bool, str]:
    if not DATADEMO.exists():
        return False, f"Không thấy thư mục: {DATADEMO}"
    pdfs = sorted(DATADEMO.glob("*.pdf"))
    if not pdfs:
        return False, f"{DATADEMO} không chứa file PDF nào"
    names = ", ".join(p.name for p in pdfs)
    return True, f"Tìm thấy {len(pdfs)} PDF: {names}"


def main() -> None:
    print("=== KIỂM TRA MÔI TRƯỜNG OCR — BUỔI 5 ===\n")
    rows = [("Python", check_python())]
    for module, label in REQUIRED_PACKAGES:
        rows.append((label, check_package(module)))
    rows.append(("datademo/", check_pdf_dir()))

    width_name = max(len(name) for name, _ in rows)
    print(f"{'Công cụ'.ljust(width_name)}  {'Trạng thái':<8}  Chi tiết")
    print("-" * (width_name + 40))
    all_ok = True
    for name, (ok, msg) in rows:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"{name.ljust(width_name)}  {status:<8}  {msg}")

    print()
    if all_ok:
        print("KẾT LUẬN: Mọi thứ đã sẵn sàng — có thể chạy pipeline OCR & chunking.")
    else:
        print("KẾT LUẬN: Có mục FAIL. Hướng khắc phục:")
        print("  1. Cài gói bị thiếu:  pip install -r requirements.txt")
        print("  2. Kiểm tra file .env trong src/ có dòng LLAMA_CLOUD_API_KEY='...'")
        print("  3. Kiểm tra thư mục datademo/ có ít nhất 1 file PDF tiếng Việt")
        print("  4. Nếu import thất bại: chạy lại bằng python của .venv:")
        print("     .venv\\Scripts\\python.exe src\\check_ocr_env.py")
        print()
        print("Các gói có thể cài thủ công:")
        print("  .venv\\Scripts\\python.exe -m pip install pymupdf pillow llama-cloud pydantic streamlit python-dotenv")
        if not shutil.which("python"):
            print("  (Cảnh báo: không tìm thấy python trong PATH — hãy dùng đường dẫn .venv)")


if __name__ == "__main__":
    main()
