# -*- coding: utf-8 -*-
"""serve_html.py — Chạy localhost để xem buoi_05_output.html.

- Serve thư mục output/ tại http://127.0.0.1:<port>
- Tự mở trình duyệt, nhấn Ctrl+C để dừng.

Chạy:
    python src/serve_html.py [port]
"""

from __future__ import annotations

import os
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUTPUT = BASE / "output"
HTML_FILE = OUTPUT / "buoi_05_output.html"
DEFAULT_PORT = 8000


def main() -> None:
    # chạy qua .vbs/pythonw không có console → stdout dùng cp1252 sẽ lỗi tiếng Việt
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None:
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    if not HTML_FILE.exists():
        print(f"Không tìm thấy {HTML_FILE.name}. Hãy chạy trước: python src/make_html.py")
        sys.exit(1)

    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    os.chdir(OUTPUT.resolve())

    # thêm header UTF-8 cho .html, tránh trình duyệt hiểu sai encoding
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            try:
                super().log_message(format, *args)
            except Exception:
                pass

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            if self.path.endswith((".html", ".htm")):
                self.send_header("Content-Type", "text/html; charset=utf-8")
            super().end_headers()

    # tự tìm cổng trống nếu cổng yêu cầu đã bị chiếm
    httpd = None
    for candidate in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        print(f"Không tìm thấy cổng trống trong khoảng {port}-{port + 9}. Hãy dừng bớt ứng dụng khác.")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}/buoi_05_output.html"
    print(f"Server chạy tại: {url}")
    print("Nhấn Ctrl+C để dừng.")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")


if __name__ == "__main__":
    main()