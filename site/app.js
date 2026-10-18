// Paradata Review: reads the batches written by scripts/build_results_site.py
// from data/ and renders them. No libraries and no network beyond this site.
"use strict";

// ?theme=light or ?theme=dark overrides the system setting, for example on a projector.
try {
  const theme = new URLSearchParams(location.search).get("theme");
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
} catch { /* the page works without it */ }

const state = { index: null, batch: null, raw: {}, view: "review", filter: "all", sort: "priority", query: "", selected: null, family: "Q", colorBy: "lane" };
const VIEWS = ["review", "data", "method", "charts", "output", "validation", "how"];
const cache = {};
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function secs(ms) {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "n/a";
  const s = ms / 1000;
  if (Math.abs(s) >= 120) return (s / 60).toFixed(1) + " min";
  if (Math.abs(s) >= 10) return s.toFixed(0) + " s";
  return s.toFixed(1) + " s";
}
function fmt(value, unit) {
  if (value === null || value === undefined) return "n/a";
  if (unit === "ms") return secs(value);
  if (unit === "pct") return (value * 100).toFixed(0) + "%";
  if (unit === "int") return String(Math.round(value));
  if (unit === "ratio") return value.toFixed(2) + "×";
  return Number(value).toFixed(3);
}
const plural = (n, word) => `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;

// A "lane" is what the reviewer does with an interview. Data-quality faults are
// their own lane: a broken record says something about the device, not the enumerator.
function lane(iv) {
  if (iv.dq) return "DQ";
  return iv.status;
}
const LANE_NAME = { FLAGGED: "Flagged", REVIEW: "Review", CLEAN: "Clean", DQ: "Data quality" };
const LANE_ORDER = { FLAGGED: 0, REVIEW: 1, DQ: 2, CLEAN: 3 };

const ACTIONS = {
  FLAGGED: ["Quarantine and open a review",
    "Hold this interview out of the dataset. Check the signals below against independent evidence, such as a back-check visit or GPS and audio audit, tell the enumerator which signals fired and hear their explanation, and record the outcome. A flag opens a review; it never concludes one."],
  REVIEW: ["Send for back-checking",
    "Add this interview to the back-check list. Some signals fired but not enough to quarantine it; fast respondents, long pauses and no navigation all have innocent causes."],
  DQ: ["Check the device and the export",
    "This record is broken: timings are missing or impossible. Re-export it or check the tablet's clock before judging the interview. The behavioural signals on a broken record are not meaningful."],
  CLEAN: ["No action", "No signal reached the review threshold. Clean interviews still enter the random back-check sample as usual."],
};

// ------------------------------------------------------------------ routing ---

function readHash() {
  const raw = location.hash.replace(/^#/, "");
  const [view, query] = raw.split("?");
  const params = new URLSearchParams(query || "");
  return { view: VIEWS.includes(view) ? view : "review",
    batch: params.get("batch"), id: params.get("id") };
}
function writeHash() {
  const params = new URLSearchParams();
  if (state.batch) params.set("batch", state.batch.label);
  if (["review", "data", "method"].includes(state.view) && state.selected) params.set("id", state.selected);
  const next = `#${state.view}?${params}`;
  if (location.hash !== next) history.replaceState(null, "", next);
}

async function getJSON(path) {
  if (!cache[path]) cache[path] = fetch(path).then((r) => { if (!r.ok) throw new Error(path); return r.json(); });
  return cache[path];
}

async function start() {
  state.index = await getJSON("data/index.json");
  const h = readHash();
  state.view = h.view;
  const label = state.index.batches.some((b) => b.label === h.batch) ? h.batch : state.index.batches[0].label;
  await selectBatch(label, h.id);
  window.addEventListener("hashchange", async () => {
    const n = readHash();
    if (n.view !== state.view) { state.view = n.view; renderView(); }
    if (n.batch && n.batch !== state.batch.label) await selectBatch(n.batch, n.id);
    else if (n.id && n.id !== state.selected) select(n.id, false);
  });
  renderFoot();
}

async function selectBatch(label, id) {
  state.batch = await getJSON(`data/${label}.json`);
  state.selected = null;
  state.filter = "all";
  renderBatches();
  renderSummary();
  renderFilters();
  renderQueue();
  const first = id && state.batch.interviews.find((x) => x.id === id) ? id : sortedQueue()[0]?.id;
  if (first) select(first, false); else $("#detail").innerHTML = "";
  renderOutput();
  renderValidation();
  renderHow();
  renderView();
}

function renderView() {
  for (const v of VIEWS) $(`#view-${v}`).hidden = v !== state.view;
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.view === state.view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  writeHash();
  refreshViews();
}

// ------------------------------------------------------------------ batches ---

function renderBatches() {
  $("#batch-list").innerHTML = state.index.batches.map((b) => `
    <button class="batch" data-label="${b.label}" aria-pressed="${b.label === state.batch.label}">
      <div class="batch-title">${esc(b.title)}</div>
      <div class="batch-meta">${plural(b.total, "interview")} · ${esc(b.platforms.join(" and "))}</div>
      <div class="batch-meta">${esc(b.description)}</div>
    </button>`).join("");
  document.querySelectorAll(".batch").forEach((el) => el.addEventListener("click", () => selectBatch(el.dataset.label)));
}

function renderSummary() {
  const b = state.batch, c = b.counts;
  const tile = (cls, label, value, note) => `<div class="tile ${cls}"><div class="tile-label">${label}</div>
    <div class="tile-value">${value}</div><div class="tile-note">${note}</div></div>`;
  $("#summary").innerHTML = [
    tile("", "Interviews processed", c.total.toLocaleString(),
      `${b.raw_rows.toLocaleString()} raw log rows`),
    tile("flagged", "Flagged", c.flagged, `score ${b.thresholds.flagged} or more: quarantine`),
    tile("review", "Review", c.review, `score ${b.thresholds.review} to ${b.thresholds.flagged - 1}: back-check`),
    tile("dq", "Data quality", c.dq, "broken records: check the device"),
    tile("clean", "Clean", c.clean, "no action"),
  ].join("");
}

// -------------------------------------------------------------------- queue ---

function renderFilters() {
  const counts = { all: state.batch.interviews.length, FLAGGED: 0, REVIEW: 0, DQ: 0, CLEAN: 0 };
  state.batch.interviews.forEach((iv) => counts[lane(iv)]++);
  const items = [["all", "All"], ["FLAGGED", "Flagged"], ["REVIEW", "Review"], ["DQ", "Data quality"], ["CLEAN", "Clean"]];
  $("#filters").innerHTML = items.map(([key, name]) =>
    `<button class="chip" data-filter="${key}" aria-pressed="${state.filter === key}">${name}<span class="count">${counts[key]}</span></button>`).join("");
  document.querySelectorAll(".chip").forEach((el) => el.addEventListener("click", () => {
    state.filter = el.dataset.filter; renderFilters(); renderQueue();
  }));
}

function sortedQueue() {
  const q = state.query.trim().toLowerCase();
  let list = state.batch.interviews.filter((iv) =>
    (state.filter === "all" || lane(iv) === state.filter) && (!q || iv.id.toLowerCase().includes(q)));
  const byId = (a, b) => a.id.localeCompare(b.id, undefined, { numeric: true });
  if (state.sort === "id") list.sort(byId);
  else if (state.sort === "score") list.sort((a, b) => b.score - a.score || byId(a, b));
  else list.sort((a, b) => LANE_ORDER[lane(a)] - LANE_ORDER[lane(b)] || b.score - a.score || byId(a, b));
  return list;
}

function reasonsSummary(iv) {
  if (iv.dq) return "Broken record";
  const names = iv.flags.filter((f) => f.kind !== "dq").map((f) => f.label);
  if (!names.length) return "None";
  return names.slice(0, 2).join(", ") + (names.length > 2 ? ` +${names.length - 2}` : "");
}

function renderQueue() {
  const list = sortedQueue();
  $("#queue-body").innerHTML = list.length ? list.map((iv) => `
    <tr class="row" tabindex="0" data-id="${esc(iv.id)}" aria-selected="${iv.id === state.selected}">
      <td class="id">${esc(iv.id)}</td>
      <td><span class="pill ${lane(iv)}">${LANE_NAME[lane(iv)]}</span></td>
      <td class="num">${iv.score}</td>
      <td class="reasons">${esc(reasonsSummary(iv))}</td>
    </tr>`).join("") : `<tr><td colspan="4" class="empty">No interviews match.</td></tr>`;
  $("#queue-foot").textContent = `Showing ${list.length} of ${state.batch.interviews.length}. Sorted by ${
    state.sort === "priority" ? "what to look at first: flagged, then review, then data quality, then clean" : state.sort === "score" ? "score" : "interview ID"}.`;
  document.querySelectorAll("tr.row").forEach((tr) => {
    tr.addEventListener("click", () => select(tr.dataset.id, true));
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(tr.dataset.id, true); }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const next = e.key === "ArrowDown" ? tr.nextElementSibling : tr.previousElementSibling;
        if (next && next.dataset.id) { next.focus(); select(next.dataset.id, false); }
      }
    });
  });
}

// ------------------------------------------------------------------- detail ---

function select(id, scroll) {
  state.selected = id;
  document.querySelectorAll("tr.row").forEach((tr) => tr.setAttribute("aria-selected", tr.dataset.id === id));
  renderDetail();
  refreshViews();
  writeHash();
  if (scroll && window.matchMedia("(max-width: 900px)").matches) $("#detail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function chart(iv) {
  const b = state.batch, ys = iv.rt, base = b.batch_rt;
  const n = Math.max(ys.length, base.length);
  if (!n) return `<p class="muted">No per-question timings were recorded for this interview.</p>`;
  const W = 600, H = 210, L = 40, R = 10, T = 12, B = 30;
  const vals = [...ys, ...base].filter((v) => v !== null && v !== undefined).map((v) => v / 1000);
  const top = Math.max(1, Math.ceil(Math.max(...vals) / 2) * 2);
  const x = (i) => L + (n === 1 ? 0 : (i * (W - L - R)) / (n - 1));
  const y = (v) => T + (H - T - B) * (1 - v / top);
  const path = (arr) => arr.map((v, i) => (v === null || v === undefined ? null : `${x(i).toFixed(1)},${y(v / 1000).toFixed(1)}`))
    .filter(Boolean).join(" ");
  const ticks = [0, top / 2, top];
  const every = n > 24 ? 5 : n > 12 ? 2 : 1;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Response time per question for ${esc(iv.id)} against the batch median">
    ${ticks.map((t) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${t}s</text>`).join("")}
    ${Array.from({ length: n }, (_, i) => (i % every === 0 || i === n - 1) ? `<text x="${x(i)}" y="${H - 10}" text-anchor="middle">${i + 1}</text>` : "").join("")}
    <polyline class="baseline" points="${path(base)}"/>
    <polyline class="series" points="${path(ys)}"/>
    ${ys.map((v, i) => (v === null || v === undefined) ? "" : `<circle class="dot" cx="${x(i)}" cy="${y(v / 1000)}" r="2.6"><title>Question ${i + 1}, ${esc(b.questions[i] || "")}: ${secs(v)} (batch median ${secs(base[i])})</title></circle>`).join("")}
  </svg>
  <div class="legend"><span style="--swatch:var(--series)"><i></i>This interview</span><span class="dashed" style="--swatch:var(--baseline)"><i></i>Batch median</span><em>Question number, in instrument order</em></div>`;
}

function renderDetail() {
  const b = state.batch;
  const iv = b.interviews.find((x) => x.id === state.selected);
  if (!iv) { $("#detail").innerHTML = `<p class="empty">Choose an interview from the queue.</p>`; return; }
  const ln = lane(iv);
  const [actionTitle, actionText] = ACTIONS[ln];
  const groups = [
    ["dq", "Data-quality faults", "Problems with the record itself."],
    ["rule", "Behaviour signals", "Each adds one point to the score."],
    ["iqr", "Statistical fences", "Values far outside this batch; together they add at most one point."],
  ];
  const reasons = groups.map(([kind, title, note]) => {
    const fs = iv.flags.filter((f) => f.kind === kind);
    if (!fs.length) return "";
    return `<h3>${title} <span class="muted small">· ${note}</span></h3><ul class="reasons-list">${fs.map((f) => `
      <li><span class="reason-label">${esc(f.label)}</span><span class="reason-kind mono">${esc(f.flag)}</span>
      <div class="reason-text">${esc(f.text)}</div></li>`).join("")}</ul>`;
  }).join("");
  const compare = b.key_features.map((k) => {
    const v = iv.f[k.name], m = b.batch[k.name];
    const far = v !== null && m ? (v / m < 0.5 || v / m > 2) : false;
    return `<tr><td>${esc(k.label)}</td><td class="num ${far ? "diff-high" : ""}">${fmt(v, k.unit)}</td><td class="num">${fmt(m, k.unit)}</td></tr>`;
  }).join("");
  $("#detail").innerHTML = `
    <div class="detail-head">
      <span class="detail-id">${esc(iv.id)}</span>
      <span class="pill ${ln}">${LANE_NAME[ln]}</span>
      <span class="score-line">Score ${iv.score} · review at ${b.thresholds.review}, flagged at ${b.thresholds.flagged} · ${esc(iv.file)}</span>
      <button class="copy" id="copy-link" type="button">Copy link</button>
    </div>
    <div class="action ${ln}"><strong>${actionTitle}</strong>${actionText}</div>
    ${iv.flags.length ? `<h2>Why</h2>${reasons}` : `<h2>Why</h2><p class="muted">No signal fired.</p>`}
    <h3>Response time per question</h3>
    ${chart(iv)}
    <h3>Against the batch</h3>
    <div class="table-wrap"><table class="compare"><thead><tr><th>Feature</th><th class="num">This interview</th><th class="num">Batch median</th></tr></thead><tbody>${compare}</tbody></table></div>
    <p class="muted small">Values more than twice or under half the batch median are highlighted. Thresholds come from this batch, which is why batches should pool all enumerators.</p>
    <details id="raw-details"><summary>Raw audit log rows</summary><div id="raw-rows" class="muted small">Loading…</div></details>`;
  $("#copy-link").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(location.href); e.target.textContent = "Copied"; } catch { e.target.textContent = "Copy failed"; }
  });
  $("#raw-details").addEventListener("toggle", async (e) => { if (e.target.open) await renderRaw(iv.id); });
}

async function renderRaw(id) {
  const raw = await getJSON(`data/raw_${state.batch.label}.json`);
  const r = raw[id];
  const box = $("#raw-rows");
  if (!box) return;
  if (!r) { box.textContent = "No raw rows found."; return; }
  box.innerHTML = `<p class="muted small">${plural(r.rows.length, "row")} from ${esc(r.file)}, exactly as exported.</p>
    <div class="table-wrap raw"><table><thead><tr>${r.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${r.rows.map((row) => `<tr>${row.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------------- output ---

function renderOutput() {
  const b = state.batch;
  $("#run-log").innerHTML = esc(b.log)
    .replace(/^(\$ .*)$/m, '<span class="cmd">$1</span>')
    .replace(/^(Precision=.*|Acceptance checks:.*)$/gm, '<span class="ok">$1</span>');
  $("#file-list").innerHTML = b.files.map((f) => `
    <button class="file" data-path="${esc(f.path)}" aria-pressed="false">
      <div class="file-name">${esc(f.name)}</div>
      <div class="file-meta">${f.rows.toLocaleString()} rows × ${f.columns} columns · ${(f.bytes / 1024).toFixed(0)} KB</div>
      <div class="file-meta">${esc(f.note)}</div>
    </button>`).join("");
  document.querySelectorAll(".file").forEach((el) => el.addEventListener("click", () => {
    document.querySelectorAll(".file").forEach((x) => x.setAttribute("aria-pressed", x === el));
    previewFile(b.files.find((f) => f.path === el.dataset.path));
  }));
  previewFile(null);
}

function parseCSV(text) {
  const rows = []; let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false; } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

async function previewFile(file) {
  const box = $("#file-preview");
  if (!file) { box.innerHTML = ""; return; }
  box.innerHTML = `<p class="muted">Loading ${esc(file.name)}…</p>`;
  const text = await fetch(file.path).then((r) => r.text());
  const rows = parseCSV(text).filter((r) => r.length > 1 || r[0]);
  const LIMIT = 200;
  const head = rows[0] || [], body = rows.slice(1, LIMIT + 1);
  const numeric = head.map((_, j) => body.every((r) => r[j] === "" || r[j] === "NaN" || !Number.isNaN(Number(r[j]))));
  const show = (v, j) => {
    if (numeric[j] && v !== "" && v !== "NaN" && !Number.isInteger(Number(v))) return Number(v).toLocaleString(undefined, { maximumFractionDigits: 3 });
    return v;
  };
  box.innerHTML = `<div class="preview-head"><h3>${esc(file.name)}</h3>
    <span class="muted small">Showing ${Math.min(LIMIT, rows.length - 1).toLocaleString()} of ${(rows.length - 1).toLocaleString()} rows · <a href="${esc(file.path)}" download>Download CSV</a></span></div>
    <div class="table-wrap preview"><table><thead><tr>${head.map((h, j) => `<th class="${numeric[j] ? "num" : ""}">${esc(h)}</th>`).join("")}</tr></thead>
    <tbody>${body.map((r) => `<tr>${r.map((v, j) => `<td class="${numeric[j] ? "num" : ""}">${esc(show(v, j))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

// --------------------------------------------------------------- validation ---

function renderValidation() {
  const b = state.batch, m = b.validation.metrics, truth = b.validation.truth;
  const wrong = b.interviews.filter((iv) => {
    const actual = truth[iv.id] && truth[iv.id] !== "normal";
    const predicted = iv.status !== "CLEAN";
    return actual !== predicted;
  });
  const tile = (label, value, note) => `<div class="tile"><div class="tile-label">${label}</div><div class="tile-value">${value}</div><div class="tile-note">${note}</div></div>`;
  $("#view-validation").innerHTML = `
    <div class="card">
      <h2>How we know the queue is right</h2>
      <p>In the field nobody knows which interviews are genuine; that is why the queue exists. These batches are synthetic, so every interview was generated with a known label: normal, fabricated, speeding, disengaged or a broken record. Comparing the queue with those labels measures the method. The detector never sees the labels.</p>
    </div>
    <div class="tiles">
      ${tile("Precision", m.precision.toFixed(3), `of interviews sent for review, the share that were anomalous · target ${m.precision_threshold}`)}
      ${tile("Recall", m.recall.toFixed(3), `of anomalous interviews, the share the queue caught · target ${m.recall_threshold}`)}
      ${tile("F1", m.f1_score.toFixed(3), "balance of the two")}
      ${tile("Interviews", m.total_samples, `${m.anomalies_true} labelled anomalous`)}
    </div>
    <div class="grid-2">
      <div class="card"><h2>Queue against labels</h2>
        <div class="table-wrap"><table class="confusion"><thead><tr><th></th><th>Sent for review</th><th>Left clean</th></tr></thead><tbody>
        <tr><th>Labelled anomalous</th><td>${m.true_positive}</td><td>${m.false_negative}</td></tr>
        <tr><th>Labelled normal</th><td>${m.false_positive}</td><td>${m.true_negative}</td></tr></tbody></table></div>
        <p class="muted small">"Sent for review" means review, flagged or data quality.</p>
      </div>
      <div class="card"><h2>Caught, by type of problem</h2><div class="bars">
        ${b.validation.by_type.map((r) => `<div class="bar-row"><span>${esc(r.anomaly_type.replace("dq_issue", "broken record"))}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${(r.detection_rate * 100).toFixed(1)}%"></span></span>
          <span class="muted">${r.detected} of ${r.total}</span></div>`).join("")}</div></div>
    </div>
    <div class="card"><h2>Where the queue and the labels disagree</h2>
      ${wrong.length ? `<div class="table-wrap"><table><thead><tr><th>Interview</th><th>Label</th><th>Queue</th><th class="num">Score</th></tr></thead><tbody>
        ${wrong.map((iv) => `<tr><td class="id"><a href="#review?batch=${b.label}&id=${encodeURIComponent(iv.id)}">${esc(iv.id)}</a></td><td>${esc(truth[iv.id])}</td><td><span class="pill ${lane(iv)}">${LANE_NAME[lane(iv)]}</span></td><td class="num">${iv.score}</td></tr>`).join("")}
        </tbody></table></div>` : `<p class="muted">None in this batch. Open the harder batch above to see where the queue and the labels disagree.</p>`}
    </div>
    ${state.index.notebook ? `<div class="card"><h2>Audit notebook</h2><p>The project's audit notebook recomputes every score from the exported features and checks it against the pipeline, then plots the score distribution and feature relationships. It was executed on the ${esc(state.index.notebook.replace("_", " "))} batch when this site was built.</p><p><a href="notebook.html">Open the executed notebook</a></p></div>` : ""}`;
}

// ---------------------------------------------------------------------- how ---

function renderHow() {
  const b = state.batch;
  $("#view-how").innerHTML = `
    <div class="card"><h2>How a survey team uses it</h2>
      <p>Every SurveyCTO and ODK interview already records an audit log: when each question opened, how long it took, when the enumerator went back. The pipeline turns a day's logs into this review queue. The cycle below is the operating procedure proposed in section 7 of the project report.</p></div>
    <ol class="steps">
      <li><strong>Export the day's audit logs</strong><p>Download the audit logs for every interview uploaded that day, from all enumerators together. Either platform, or both mixed.</p></li>
      <li><strong>Run one command</strong><p>The data manager runs the pipeline on the export. It detects each platform by itself.</p>
        <pre class="cmd-block">python run_pipeline.py --inputs exports/*.csv --label 2026-10-19</pre></li>
      <li><strong>Review the queue each morning</strong><p>Flagged interviews first, then review, then broken records. Every interview states why it is where it is.</p></li>
      <li><strong>Act, then record the outcome</strong><p>Quarantine flagged interviews and back-check review ones. Tell enumerators which signals fired and hear their explanation. Record what the check found.</p></li>
    </ol>
    <div class="grid-2" style="margin-top:16px">
      <div class="card"><h2>What it needs to be right</h2>
        <p><strong>Pool the batch.</strong> Thresholds are measured from the batch itself, so most of it must be genuine. Run it on all enumerators' uploads together, never one caseload alone; past half the batch anomalous, detection fails.</p>
        <p><strong>Join to the survey data for names.</strong> Audit logs carry an interview ID but not the enumerator. Joining the queue to the survey's own records on that ID gives a per-enumerator view.</p>
        <p><strong>Recalibrate for a new instrument.</strong> Defaults suit a twenty-question household survey; the repository includes a recalibration script.</p></div>
      <div class="card"><h2>What this site is</h2>
        <p>Each batch above was run through the real pipeline, unchanged, when this site was built from the repository; the run output tab shows its console output and files. In a survey the same command runs on the data manager's computer or a team server, and produces the same files.</p>
        <p>This batch: ${plural(b.raw_rows, "raw log row")} from ${esc(b.inputs.join(" and "))}.</p></div>
    </div>`;
}

function renderFoot() {
  const i = state.index;
  $("#foot").innerHTML = `Built from commit <code>${esc(i.version)}</code> on ${esc(i.built)}. Final Year Project, University of Zambia, 2026 · <a href="health">status</a>`;
}

document.querySelectorAll(".tabs a").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault(); state.view = a.dataset.view; renderView(); window.scrollTo({ top: 0 });
}));
$("#search").addEventListener("input", (e) => { state.query = e.target.value; renderQueue(); });
$("#sort").addEventListener("change", (e) => { state.sort = e.target.value; renderQueue(); });

start().catch((err) => {
  $("#app").innerHTML = `<div class="card"><h2>Could not load the batches</h2><p class="muted">${esc(err.message)}. The site must be served over HTTP, for example with <code>python -m http.server</code> in the site folder.</p></div>`;
});
