# -*- coding: utf-8 -*-
"""Render a comment review page from a reviewer spec.

The page shows each item with its previous text, the code around it, options
a/b(/c)/d with the recommendation marked, and a comment box. Choices persist
through the hosting runtime's document store when available (collection
"reviews/<id>/items"); otherwise the page offers a copyable answer string.

usage: review_page.py --project <dir> --spec spec.json --out review.html
Refuses a spec where an item lacks a, an alternative, d, or a valid rec.
"""
import argparse, html, json, os, sys


def context(project, rel, needle):
    path = os.path.join(project, rel)
    lines = open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    idx = [i for i, l in enumerate(lines) if needle in l]
    if len(idx) != 1:
        raise SystemExit(f"needle must occur exactly once: {rel!r} {needle!r} ({len(idx)} hits)")
    i = idx[0]
    start = i
    while start > 0 and lines[start - 1].strip().startswith("///"):
        start -= 1
    lo, hi = max(0, start - 2), min(len(lines), i + 7)
    return i + 1, [(n + 1, lines[n], start <= n <= i or (lines[n].strip().startswith("///") and i < n < i + 3)) for n in range(lo, hi)]


def validate(spec):
    for it in spec["items"]:
        keys = [o["k"] for o in it["options"]]
        if "a" not in keys:
            raise SystemExit(f"item {it['id']}: option a missing")
        if not any(k in keys for k in ("b", "c")):
            raise SystemExit(f"item {it['id']}: no alternative (b/c)")
        if "d" not in keys:
            it["options"].append({"k": "d", "text": "삭제"})
            keys.append("d")
        if it.get("rec") not in keys:
            raise SystemExit(f"item {it['id']}: rec {it.get('rec')!r} not among options")
        if it.get("kind") not in ("judge", "prec"):
            raise SystemExit(f"item {it['id']}: kind must be judge or prec")


PAGE = r"""<title>주석 검수 #__RID__</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root {
  --bg: #f6f5f1; --panel: #ffffff; --fg: #1f2328; --muted: #6b7280; --line: #dcd9d1;
  --code-bg: #f1efe8; --hl: #fff3c4; --accent: #b45309; --accent-fg: #ffffff;
  --judge: #b45309; --judge-bg: #fdf1e3; --prec: #3f6e5a; --prec-bg: #e7f1ec;
  --sel: #1f2328; --rec: #8a5a00;
  --sans: "Noto Sans KR", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", Consolas, "Courier New", monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #16181c; --panel: #1f2227; --fg: #e6e4df; --muted: #9aa0a8; --line: #31353c;
  --code-bg: #15171a; --hl: #3a3417; --accent: #e0a24a; --accent-fg: #1a1a1a;
  --judge: #e0a24a; --judge-bg: #3a2c16; --prec: #8ec5ab; --prec-bg: #1d3328;
  --sel: #e6e4df; --rec: #e0a24a; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #16181c; --panel: #1f2227; --fg: #e6e4df; --muted: #9aa0a8; --line: #31353c;
  --code-bg: #15171a; --hl: #3a3417; --accent: #e0a24a; --accent-fg: #1a1a1a;
  --judge: #e0a24a; --judge-bg: #3a2c16; --prec: #8ec5ab; --prec-bg: #1d3328;
  --sel: #e6e4df; --rec: #e0a24a; color-scheme: dark; }
body { background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 14px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 0 48px; }
.wrap { max-width: 880px; margin: 0 auto; }
header.top { position: sticky; top: env(safe-area-inset-top, 0px); background: var(--bg); z-index: 5; padding-block: 14px 10px; border-bottom: 1px solid var(--line); margin-bottom: 18px; }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--bg); }
h1 { font-size: 18px; margin: 0; font-weight: 700; text-wrap: balance; }
.sub { color: var(--muted); font-size: 12.5px; margin-top: 2px; }
.status { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 8px; font-size: 12.5px; }
.status .pill { border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; font-variant-numeric: tabular-nums; }
.status .pill.ok { border-color: var(--prec); color: var(--prec); }
.status .pill.warn { border-color: var(--judge); color: var(--judge); }
button { font: inherit; border: 1px solid var(--line); background: var(--panel); color: var(--fg); border-radius: 6px; padding: 5px 12px; cursor: pointer; }
button.primary { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); font-weight: 500; }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
h2 { font-size: 14px; margin: 26px 0 10px; color: var(--muted); font-weight: 500; letter-spacing: .04em; text-transform: uppercase; }
.lead { color: var(--muted); font-size: 13px; margin: -4px 0 12px; }
.item { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px 12px; margin-bottom: 12px; min-width: 0; }
.item.answered { border-color: color-mix(in srgb, var(--prec) 55%, var(--line)); }
.head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.num { font-family: var(--mono); font-weight: 500; font-size: 13px; }
.file { font-family: var(--mono); font-size: 12px; color: var(--muted); min-width: 0; overflow-wrap: anywhere; }
.badge { font-size: 11px; padding: 1px 8px; border-radius: 999px; font-weight: 500; }
.badge.judge { background: var(--judge-bg); color: var(--judge); }
.badge.prec { background: var(--prec-bg); color: var(--prec); }
.note { font-size: 12.5px; color: var(--muted); margin: -4px 0 8px; }
.prev { display: grid; grid-template-columns: auto 1fr; gap: 8px; align-items: start; font-size: 12.5px; margin-bottom: 8px; min-width: 0; }
.prev .lbl { font-size: 11px; border: 1px solid var(--line); border-radius: 999px; padding: 0 6px; color: var(--muted); white-space: nowrap; }
.prev .lbl.new { border-color: var(--judge); color: var(--judge); }
.prev .t { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; }
.prev .t.muted { font-family: var(--sans); color: var(--muted); }
pre { margin: 0 0 10px; background: var(--code-bg); border-radius: 6px; padding: 8px 0; overflow-x: auto; font-family: var(--mono); font-size: 12px; line-height: 1.5; }
pre .ln { display: block; padding: 0 12px; white-space: pre; }
pre .ln.hl { background: var(--hl); }
pre .ln .n { display: inline-block; width: 3.2em; color: var(--muted); user-select: none; }
.opts { display: grid; gap: 6px; }
.opt { display: grid; grid-template-columns: auto auto 1fr; gap: 8px; align-items: start; padding: 6px 8px; border: 1px solid transparent; border-radius: 6px; cursor: pointer; min-width: 0; }
.opt:hover { border-color: var(--line); }
.opt.on { border-color: var(--sel); }
.opt input { margin-top: 4px; }
.opt .k { font-family: var(--mono); font-weight: 500; width: 1.2em; padding-top: 1px; }
.opt .t { font-family: var(--mono); font-size: 12.5px; white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; }
.opt .t.del { font-family: var(--sans); color: var(--muted); }
.opt .rec { font-size: 11px; color: var(--rec); margin-left: 6px; font-family: var(--sans); border: 1px solid currentColor; border-radius: 999px; padding: 0 6px; }
.opt .rec.cur { color: var(--muted); }
textarea { width: 100%; box-sizing: border-box; margin-top: 8px; font: inherit; font-size: 13px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--fg); resize: vertical; min-height: 34px; }
details { border: 1px dashed var(--line); border-radius: 8px; padding: 6px 12px; margin-bottom: 12px; }
summary { cursor: pointer; font-size: 13px; color: var(--muted); }
.foot { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--line); }
.foot .out { font-family: var(--mono); font-size: 12px; color: var(--muted); overflow-wrap: anywhere; }
@media (prefers-reduced-motion: no-preference) { .item { transition: border-color .15s; } }
</style>
<div class="wrap">
<header class="top">
  <h1>주석 검수 #__RID__ — __TITLE__</h1>
  <div class="sub">판단 필요 __JUDGE__개는 고르고, 선례 적용 __PREC__개는 훑어보다 걸리는 것만 바꿔. 코멘트는 자유. 저장은 자동.</div>
  <div class="status">
    <span class="pill" id="saved">저장소 연결 중…</span>
    <span class="pill" id="count">판단 0/__JUDGE__</span>
    <button class="primary" id="done">검수 완료</button>
    <span id="doneState" class="pill" hidden>완료 표시됨</span>
  </div>
</header>
<h2>판단 필요</h2>
<p class="lead">새 문장이거나 어휘가 걸리는 것. 항목마다 수정 전 문장(없으면 신규)을 먼저 보여주고, a는 이번 작업에서 쓴 문장. 추천은 선택지 옆에 표시.</p>
<div id="judge"></div>
<h2>선례 적용</h2>
<p class="lead">기존 문형을 그대로 따른 것. 어떤 선례인지 각 항목에 적어뒀어. 그대로면 안 건드려도 되고, 새로 가야 하면 코멘트.</p>
<details><summary>__PREC__개 펼치기</summary><div id="prec"></div></details>
<div class="foot">
  <button id="copy">답 복사 (채팅용)</button>
  <span class="out" id="out"></span>
</div>
</div>
<script>
const RID = "__RID__";
const ITEMS = __DATA__;
const state = {};
let db = null, col = null, saving = 0;
const $ = (s, r = document) => r.querySelector(s);
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render() {
  for (const it of ITEMS) {
    const host = $(it.kind === "judge" ? "#judge" : "#prec");
    const el = document.createElement("section");
    el.className = "item"; el.id = "i" + it.id;
    const code = it.ctx.map(l => `<span class="ln${l.hl ? " hl" : ""}"><span class="n">${l.n}</span>${esc(l.t)}</span>`).join("");
    const opts = it.options.map(o => `<label class="opt" data-k="${o.k}"><input type="radio" name="c${it.id}" id="c${it.id}${o.k}" value="${o.k}"><span class="k">${o.k}</span><span class="t${o.k === "d" ? " del" : ""}">${esc(o.text)}${o.k === "a" ? '<span class="rec cur">이번 작성</span>' : ""}${o.k === it.rec ? '<span class="rec">추천</span>' : ""}</span></label>`).join("");
    el.innerHTML = `<div class="head"><span class="num">#${it.id}</span><span class="badge ${it.kind}">${it.kind === "judge" ? "판단 필요" : "선례 적용"}</span><span class="file">${esc(it.file)}:${it.line}</span></div>
      ${it.note ? `<div class="note">${it.kind === "prec" ? "선례: " : ""}${esc(it.note)}</div>` : ""}
      <div class="prev">${it.prev ? `<span class="lbl">수정 전</span><span class="t">${esc(it.prev)}</span>` : `<span class="lbl new">신규</span><span class="t muted">수정 전 코드에 없던 주석</span>`}</div>
      <pre>${code}</pre>
      <div class="opts">${opts}</div>
      <textarea id="m${it.id}" rows="1" placeholder="코멘트 (다른 문장, 이유, 질문)"></textarea>`;
    host.appendChild(el);
    el.querySelectorAll("input[type=radio]").forEach(r => r.addEventListener("change", () => setChoice(it.id, r.value)));
    const ta = $("#m" + it.id, el);
    let timer;
    ta.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => setComment(it.id, ta.value), 700); });
    ta.addEventListener("blur", () => { clearTimeout(timer); setComment(it.id, ta.value); });
  }
}
function paint(id) {
  const s = state[id] || {};
  const el = $("#i" + id);
  if (!el) return;
  el.querySelectorAll(".opt").forEach(o => o.classList.toggle("on", o.dataset.k === s.choice));
  const r = s.choice ? $(`#c${id}${s.choice}`, el) : null;
  if (r) r.checked = true;
  const ta = $("#m" + id, el);
  if (document.activeElement !== ta && (s.comment || "") !== ta.value) ta.value = s.comment || "";
  el.classList.toggle("answered", !!(s.choice || s.comment));
  const n = ITEMS.filter(i => i.kind === "judge" && (state[i.id] || {}).choice).length;
  $("#count").textContent = `판단 ${n}/${ITEMS.filter(i => i.kind === "judge").length}`;
}
async function persist(id) {
  const s = state[id];
  if (!col) return;
  saving++; $("#saved").textContent = "저장 중…";
  try { await col.doc(String(id)).set({ choice: s.choice || "", comment: s.comment || "", at: new Date().toISOString() }); }
  catch (e) { $("#saved").textContent = "저장 실패: " + (e && e.code || "unknown"); $("#saved").className = "pill warn"; saving--; return; }
  saving--; if (saving === 0) { $("#saved").textContent = "저장됨"; $("#saved").className = "pill ok"; }
}
function setChoice(id, k) { state[id] = Object.assign({}, state[id], { choice: k }); paint(id); persist(id); }
function setComment(id, v) { const cur = (state[id] || {}).comment || ""; if (cur === v) return; state[id] = Object.assign({}, state[id], { comment: v }); paint(id); persist(id); }
$("#copy").addEventListener("click", () => {
  const parts = ITEMS.map(i => { const s = state[i.id] || {}; if (!s.choice && !s.comment) return null; return `${i.id}${s.choice || "?"}${s.comment ? "(" + s.comment.replace(/\s+/g, " ") + ")" : ""}`; }).filter(Boolean);
  const text = parts.join(" ") || "(선택 없음)";
  $("#out").textContent = text;
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).catch(() => {});
});
$("#done").addEventListener("click", async () => {
  if (!db) { $("#doneState").hidden = false; $("#doneState").textContent = "저장소 없음. 답 복사로 전달"; return; }
  try { await db.doc("reviews/" + RID).set({ done: true, at: new Date().toISOString() }); $("#doneState").hidden = false; }
  catch (e) { $("#doneState").hidden = false; $("#doneState").textContent = "완료 표시 실패"; }
});
render();
ITEMS.forEach(i => paint(i.id));
(async () => {
  db = window.claude && window.claude.use ? await window.claude.use("db") : null;
  if (!db) { $("#saved").textContent = "저장소 없음 (답 복사로 전달)"; $("#saved").className = "pill warn"; return; }
  col = db.collection("reviews/" + RID + "/items");
  col.onSnapshot(snap => {
    for (const d of snap.docs) { const b = d.data() || {}; state[d.id] = { choice: b.choice || "", comment: b.comment || "" }; paint(Number(d.id)); }
    if (saving === 0) { $("#saved").textContent = snap.empty ? "저장 준비됨" : "저장됨"; $("#saved").className = "pill ok"; }
  }, e => { $("#saved").textContent = "저장소 오류: " + e.code; $("#saved").className = "pill warn"; });
  db.doc("reviews/" + RID).onSnapshot(s => { if (s.exists && s.data().done) $("#doneState").hidden = false; });
})();
</script>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    spec = json.load(open(a.spec, encoding="utf-8"))
    validate(spec)
    items = []
    for it in spec["items"]:
        line, ctx = context(a.project, it["file"], it["needle"])
        items.append({"id": it["id"], "file": it["file"], "line": line, "kind": it["kind"], "note": it.get("note", ""), "rec": it["rec"],
                      "prev": it.get("prev"), "options": it["options"], "ctx": [{"n": n, "t": t, "hl": h} for n, t, h in ctx]})
    judge = sum(1 for i in items if i["kind"] == "judge")
    prec = len(items) - judge
    page = (PAGE.replace("__DATA__", json.dumps(items, ensure_ascii=False)).replace("__JUDGE__", str(judge)).replace("__PREC__", str(prec))
                .replace("__RID__", str(spec["id"])).replace("__TITLE__", html.escape(spec.get("title", ""))))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(page)
    print(f"{len(items)} items (judge {judge}, prec {prec}) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
