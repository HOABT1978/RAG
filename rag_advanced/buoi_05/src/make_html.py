# -*- coding: utf-8 -*-
"""make_html.py — Sinh file HTML dashboard độc lập để trình diễn Buổi 5.

Đọc dữ liệu từ output/ (raw + chunks) nhúng thẳng vào 1 file HTML
self-contained. Bố cục dashboard: tất cả 4 phần hiển thị trên cùng 1 màn
hình (PDF gốc · Text OCR · Chunk · So sánh), scroll nội bộ từng panel.

Chạy:
    python src/make_html.py
    # kết quả: output/buoi_05_output.html  (xem qua: python src/serve_html.py)
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUTPUT = BASE / "output"
RAW_DIR = OUTPUT / "raw"
CHUNK_DIR = OUTPUT / "chunks"
PAGES_DIR = OUTPUT / "pages"
OUT_HTML = OUTPUT / "buoi_05_output.html"

PAGE_RE = re.compile(r"===== TRANG (\d+) \| nguồn: (\S+) =====\n?(.*?)(?=====|$)", re.S)

STRATEGY_LABELS = {
    "fixed_size": "Fixed-size",
    "semantic": "Semantic",
    "hierarchical": "Hierarchical",
}
STRATEGY_DESC = {
    "fixed_size": "Cắt theo số ký tự cố định + overlap",
    "semantic": "Cắt theo đoạn văn, hết câu khi có thể",
    "hierarchical": "Mỗi mốc Chương/Mục/Điều/Điểm bắt đầu 1 chunk",
}
COLORS = [
    "#cfe8ff", "#ffe9c7", "#d9f0d3", "#f5d0d0", "#e3d7f5",
    "#c7ecf0", "#fbe3c9", "#d7d7f7", "#d3e8cf", "#f2d3e8",
]


def esc(s: object) -> str:
    return html_lib.escape(str(s), quote=True)


def load_documents() -> dict:
    docs = {}
    for meta_path in sorted(RAW_DIR.glob("*_raw.json")):
        stem = meta_path.name.replace("_raw.json", "")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        raw_txt = RAW_DIR / f"{stem}_raw.txt"
        pages = []
        if raw_txt.exists():
            blocks = PAGE_RE.findall(raw_txt.read_text(encoding="utf-8"))
            pages = [{"page": int(b[0]), "method": b[1], "text": b[2].rstrip()} for b in blocks]
            if not pages:
                pages = [{"page": 1, "method": "text", "text": raw_txt.read_text(encoding="utf-8")}]
        chunks = []
        chunks_path = CHUNK_DIR / f"{stem}_chunks.jsonl"
        if chunks_path.exists():
            chunks = [json.loads(l) for l in chunks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        imgs = sorted((PAGES_DIR / stem).glob("page_*.png")) if (PAGES_DIR / stem).exists() else []
        docs[stem] = {
            "meta": meta,
            "pages": pages,
            "chunks": chunks,
            "images": [f"pages/{stem}/{p.name}" for p in imgs],
        }
    return docs


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAG Foundation — Buổi 5 · Dashboard</title>
<style>
  :root { --accent:#2f6fed; --bg:#eef1f8; --card:#fff; --border:#d7deeb;
          --ink:#1e2430; --muted:#667085; --chip:#eef3ff; }
  * { box-sizing:border-box; }
  html, body { height:100%; margin:0; overflow:hidden; }
  body { font-family:"Segoe UI", Arial, sans-serif; background:var(--bg); color:var(--ink); font-size:13px; }
  .app { display:flex; flex-direction:column; height:100vh; padding:10px 14px; gap:8px; }

  /* ---- header ---- */
  header { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
           background:var(--accent); color:#fff; border-radius:10px; padding:8px 14px; }
  header h1 { margin:0; font-size:15px; white-space:nowrap; }
  header .sub { font-size:11px; opacity:.85; white-space:nowrap; }
  header .sp { flex:1; }
  .ctl { display:flex; align-items:center; gap:6px; background:rgba(255,255,255,.14);
         padding:3px 8px; border-radius:7px; white-space:nowrap; }
  .ctl label { font-size:11px; font-weight:600; opacity:.9; }
  .ctl select { padding:3px 6px; border-radius:5px; border:none; font-size:12px; color:#1e2430; }

  /* ---- metrics ---- */
  .metrics { display:flex; gap:8px; }
  .metric { flex:1; background:var(--card); border:1px solid var(--border); border-radius:8px;
            padding:5px 12px; display:flex; align-items:baseline; gap:8px; min-width:0; }
  .metric .k { font-size:11px; color:var(--muted); white-space:nowrap; }
  .metric .v { font-size:17px; font-weight:700; }

  /* ---- main grid ---- */
  .grid { flex:1; min-height:0; display:grid; grid-template-columns:0.85fr 1fr 1.35fr; gap:8px; }
  .panel { background:var(--card); border:1px solid var(--border); border-radius:10px;
           padding:8px 10px; min-height:0; display:flex; flex-direction:column; }
  .panel h3 { margin:0 0 6px; font-size:13px; display:flex; align-items:center; gap:8px; }
  .pill { display:inline-block; padding:1px 9px; border-radius:20px; font-size:11px; font-weight:600;
          background:#e7f0ff; color:#1d4ed8; }
  .scroll { flex:1; min-height:0; overflow:auto; }
  .imgbox { text-align:center; background:#fafbff; border:1px solid var(--border); border-radius:7px;
            padding:6px; height:100%; }
  .imgbox img { max-width:100%; max-height:100%; }
  pre { margin:0; background:#0f172a; color:#dbeafe; padding:10px; border-radius:7px;
        font-size:12px; line-height:1.5; white-space:pre-wrap; word-break:break-word; }
  .boundary { font-size:11px; line-height:1.5; padding:6px 8px; border:1px solid var(--border);
              border-radius:7px; background:#fbfcff; margin-bottom:6px; }
  .chunk { border:1px solid var(--border); border-radius:7px; margin:5px 0; font-size:12px; }
  .chunk summary { cursor:pointer; padding:5px 8px; font-weight:600; }
  .chunk .body { padding:6px 8px; line-height:1.5; white-space:pre-wrap; word-break:break-word; }
  .muted { font-size:11px; color:var(--muted); }
  .method { font-size:11px; color:var(--muted); margin:2px 0 4px; }

  /* ---- bottom table ---- */
  .cmp { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:8px 10px; }
  .cmp h3 { margin:0 0 6px; font-size:13px; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th, td { border:1px solid var(--border); padding:4px 10px; text-align:left; }
  th { background:#eef2fa; }
  td.strat { font-weight:600; }
  tr.active-row { background:#fff7dd; }
</style>
</head>
<body>
<div class="app">

  <header>
    <h1>📄 RAG Foundation — Buổi 5</h1>
    <span class="sub">OCR PDF tiếng Việt (Llamaparse) + 3 chiến lược chunking</span>
    <span class="sp"></span>
    <span class="ctl"><label>📚 Tài liệu</label><select id="docSel"></select></span>
    <span class="ctl"><label>✂️ Chiến lược</label>
      <select id="stratSel">
        <option value="fixed_size">Fixed-size</option>
        <option value="semantic">Semantic</option>
        <option value="hierarchical">Hierarchical</option>
      </select></span>
    <span class="ctl"><label>📄 Trang</label><select id="pageSel"></select></span>
    <span class="muted" style="color:#dbeafe">Sinh lúc __GEN__</span>
  </header>

  <div class="metrics" id="metrics"></div>

  <div class="grid">
    <div class="panel">
      <h3>1️⃣ PDF gốc <span class="muted">(render 150 dpi)</span></h3>
      <div class="scroll"><div class="imgbox" id="imgbox"></div></div>
    </div>
    <div class="panel">
      <h3>2️⃣ Text sau OCR <span class="muted">(Unicode NFC)</span></h3>
      <div class="method" id="txtMethod"></div>
      <div class="scroll"><pre id="txtView"></pre></div>
    </div>
    <div class="panel">
      <h3>3️⃣ Chunk — <span id="chunkStratName"></span> <span class="pill" id="chunkCount"></span></h3>
      <div class="boundary" id="boundary"></div>
      <div class="scroll" id="chunkList"></div>
    </div>
  </div>

  <div class="cmp">
    <h3>4️⃣ So sánh 3 chiến lược <span class="muted">— Fixed-size: đều, cắt ngang câu · Semantic: giữ trọn đoạn ·
      Hierarchical: theo Chương/Mục/Điều, dài bất đối xứng</span></h3>
    <table id="cmpTable"></table>
  </div>

</div>

<script>
const DOCS = __DATA__;
const LABELS = __LABELS__;
const DESCS = __DESCS__;
const COLORS = __COLORS__;
const STRATS = ["fixed_size", "semantic", "hierarchical"];
const esc = s => String(s).replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));

let curDoc = Object.keys(DOCS)[0] || null;
let curStrat = "fixed_size";
let curPage = 0;
const $ = id => document.getElementById(id);

function statsFor(doc, strat) {
  const lens = doc.chunks.filter(c => c.strategy === strat).map(c => c.text.length);
  if (!lens.length) return {count:0, min:0, max:0, avg:0};
  return {count:lens.length, min:Math.min(...lens), max:Math.max(...lens),
          avg:Math.round(lens.reduce((a,b)=>a+b,0)/lens.length * 10)/10};
}

function renderDocSel() {
  const s = $("docSel");
  s.innerHTML = Object.keys(DOCS).map(d => `<option>${esc(d)}</option>`).join("");
  s.value = curDoc;
}
function renderPageSel(doc) {
  const s = $("pageSel");
  s.innerHTML = doc.pages.map((p, i) => `<option value="${i}">Trang ${p.page}</option>`).join("");
  s.value = Math.min(curPage, doc.pages.length - 1);
  curPage = parseInt(s.value);
}
function renderMetrics(doc) {
  const m = doc.meta || {};
  const st = statsFor(doc, curStrat);
  const total = doc.chunks.length;
  const cells = [
    ["Số trang", doc.pages.length],
    ["OCR Llamaparse", m.ocr_used ? "✅ Có" : "❌ Không"],
    ["Số ký tự", (m.char_count || 0).toLocaleString()],
    ["Tổng chunk", total.toLocaleString()],
    ["Chunk " + LABELS[curStrat], st.count]
  ];
  $("metrics").innerHTML = cells.map(([k, v]) =>
    `<div class="metric"><div class="k">${k}</div><div class="v">${esc(v)}</div></div>`).join("");
}
function renderImage(doc) {
  const src = doc.images[curPage];
  $("imgbox").innerHTML = src ? `<img src="${esc(src)}" alt="Trang ${curPage+1}">`
                              : "<p class='muted'>Không có ảnh trang này.</p>";
}
function renderText(doc) {
  const p = doc.pages[curPage] || {text:"", method:""};
  $("txtView").textContent = p.text;
  $("txtMethod").textContent = "Nguồn trang " + (doc.pages[curPage] || {}).page +
      " — " + p.method + " · đã chuẩn hoá Unicode NFC.";
}
function renderChunk(doc) {
  $("chunkStratName").textContent = LABELS[curStrat];
  const chunks = doc.chunks.filter(c => c.strategy === curStrat);
  $("chunkCount").textContent = chunks.length + " chunk";
  let buf = "";
  for (let i = 0; i < chunks.length; i++) {
    buf += `<span style="background:${COLORS[i % COLORS.length]}">${esc(chunks[i].text)}</span>`;
    if (i < chunks.length - 1) buf += "<span style='color:red;font-weight:700'>‖</span>";
  }
  $("boundary").innerHTML = "<b>Ranh giới chunk:</b> " + buf;
  $("chunkList").innerHTML = chunks.map((c, i) => {
    const s = c.structure || {};
    const badge = s.type ? `🏷 ${esc(s.type)}${s.title ? " · " + esc(s.title) : ""}`
                         : "🏷 không có cấu trúc";
    return `<details class="chunk">
      <summary style="background:${COLORS[i % COLORS.length]}">${esc(c.chunk_id)} · trang ${c.page_start}–${c.page_end} · ${c.text.length.toLocaleString()} ký tự · ${badge}</summary>
      <div class="body">${esc(c.text)}</div>
    </details>`;
  }).join("");
}
function renderCompare(doc) {
  const rows = STRATS.map(s => {
    const st = statsFor(doc, s);
    return `<tr class="${s === curStrat ? 'active-row' : ''}">
      <td class="strat">${LABELS[s]}</td><td>${st.count}</td><td>${st.min}</td><td>${st.max}</td><td>${st.avg}</td>
    </tr>`;
  }).join("");
  $("cmpTable").innerHTML =
    "<tr><th>Chiến lược</th><th>Số chunk</th><th>Min (ký tự)</th><th>Max (ký tự)</th><th>Trung bình</th></tr>" + rows;
}
function renderAll() {
  const doc = DOCS[curDoc];
  if (!doc) return;
  renderPageSel(doc);
  renderMetrics(doc);
  renderImage(doc);
  renderText(doc);
  renderChunk(doc);
  renderCompare(doc);
}

$("docSel").addEventListener("change", e => { curDoc = e.target.value; curPage = 0; renderAll(); });
$("stratSel").addEventListener("change", e => { curStrat = e.target.value; renderMetrics(DOCS[curDoc]);
  renderChunk(DOCS[curDoc]); renderCompare(DOCS[curDoc]); });
$("pageSel").addEventListener("change", e => { curPage = parseInt(e.target.value);
  renderImage(DOCS[curDoc]); renderText(DOCS[curDoc]); });

renderDocSel();
renderAll();
</script>
</body>
</html>
"""


def main() -> None:
    docs = load_documents()
    if not docs:
        print("Không có dữ liệu trong output/. Hãy chạy: python src/pipeline.py --write")
        sys.exit(1)
    data = json.dumps(docs, ensure_ascii=False)
    html_doc = (
        HTML_TEMPLATE
        .replace("__DATA__", data)
        .replace("__LABELS__", json.dumps(STRATEGY_LABELS, ensure_ascii=False))
        .replace("__DESCS__", json.dumps(STRATEGY_DESC, ensure_ascii=False))
        .replace("__COLORS__", json.dumps(COLORS))
        .replace("__GEN__", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    total_chunks = sum(len(d["chunks"]) for d in docs.values())
    print(f"Đã tạo: {OUT_HTML}")
    print(f"Tài liệu: {', '.join(docs.keys())}")
    print(f"Tổng chunk: {total_chunks:,}")
    print(f"Dung lượng: {OUT_HTML.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
