// The explainer views: the shape of the input data, the method, and the charts.
// They read what scripts/build_results_site.py wrote and use helpers from app.js.
"use strict";

const MS_IDS = new Set(["Q-01", "Q-02", "Q-07", "Q-10", "S-01", "S-02", "S-07", "S-08", "V-01", "V-02", "V-03", "T-02", "T-06", "T-07", "T-09", "T-10"]);
const RATE_IDS = new Set(["V-05", "S-10"]);
function fmtFeature(column, value) {
  if (value === null || value === undefined) return "n/a";
  const id = column.slice(0, 4);
  if (MS_IDS.has(id)) return secs(value);
  if (RATE_IDS.has(id)) return (value * 100).toFixed(0) + "%";
  if (id === "V-09") return value.toFixed(2) + "×";
  return Number.isInteger(value) ? String(value) : Number(value).toPrecision(3);
}
const code = (text) => esc(text).replace(/`([^`]+)`/g, "<code>$1</code>");
const pct1 = (v) => (v === null || v === undefined ? "n/a" : (v * 100).toFixed(1) + "%");

const COLUMN_NOTES = {
  SurveyCTO: {
    interview_id: "Which interview the row belongs to.",
    node: "The question (field) the event is about. Empty on the form's start and end rows.",
    event: "What happened: question-end, jump, form-start, form-end, constraint.",
    start: "When the event began, in epoch milliseconds (milliseconds since 1 January 1970).",
    end: "When the event finished, in epoch milliseconds.",
    duration_ms: "How long it lasted: end minus start.",
  },
  ODK: {
    instance_id: "Which interview (form instance) the row belongs to.",
    name: "The question (field) the event is about. Empty on the form's start and end rows.",
    event: "What happened: question-end, jump, form start, form end, constraint.",
    start_time: "When the event began, as an ISO 8601 timestamp with a time zone.",
    end_time: "When the event finished, as an ISO 8601 timestamp.",
  },
};

const EVENT_MAP = [
  ["form-start, form start", "form_start", "The interview opens."],
  ["question-start, question, group questions", "field_start", "A question comes on screen."],
  ["question-end", "field_end", "The enumerator moves on from a question. Its duration is the time spent."],
  ["jump", "jump", "The enumerator navigates, usually back. Counted as back-navigation."],
  ["form-end, end screen", "form_end", "The interview closes."],
  ["constraint", "constraint", "A validation rule fired on an answer."],
  ["form save, exit, resume, finalize", "form_save, …", "Administrative events. Kept, but left out of the section statistics."],
];

// -------------------------------------------------------------- the picker ---

function pickerHTML(id) {
  const options = state.batch.interviews.map((iv) => `<option value="${esc(iv.id)}"></option>`).join("");
  return `<div class="picker"><label>Interview <input class="id-input" list="id-list" value="${esc(id)}" autocomplete="off" spellcheck="false"></label>
    <span class="muted small">Type an ID, or choose one in the review queue. This page follows your choice.</span>
    <datalist id="id-list">${options}</datalist></div>`;
}
function bindPicker(root) {
  const input = root.querySelector(".id-input");
  if (!input) return;
  input.addEventListener("change", () => {
    const id = input.value.trim();
    if (state.batch.interviews.some((iv) => iv.id === id)) select(id, false);
    else input.value = state.selected;
  });
}

// ------------------------------------------------------------------ data in ---

let dataToken = 0;
async function renderData() {
  const box = $("#view-data");
  if (!state.batch) return;
  const token = ++dataToken;
  const b = state.batch, id = state.selected || b.interviews[0].id;
  const raw = (await getJSON(`data/raw_${b.label}.json`))[id];
  if (token !== dataToken) return;
  if (!raw) { box.innerHTML = `<div class="card"><p class="empty">No raw rows for this interview.</p></div>`; return; }
  const platform = b.sources.find((s) => s.file === raw.file)?.platform || b.sources[0].platform;
  const notes = COLUMN_NOTES[platform];
  const table = (columns, rows, cls = "") => `<div class="table-wrap raw ${cls}"><table><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  const maxEvents = Math.max(...b.sources.flatMap((s) => Object.values(s.events)));

  box.innerHTML = `
    <div class="card notice-card"><strong>What these files are.</strong> The layouts below are the ones the pipeline was built and evaluated on. They follow the structure of ODK Collect's and SurveyCTO's audit logs, but they are this project's synthetic layouts, not the platforms' native exports. The pipeline also recognises ODK's native <code>audit.csv</code>. SurveyCTO's native text audit is not supported yet.</div>

    <div class="card"><h2>1. What was uploaded</h2>
      <p class="muted">An audit log is one row per event. A survey platform writes one for every interview, and a batch is the day's files together.</p>
      <div class="source-grid">${b.sources.map((s) => `<div class="source">
        <div class="source-name">${esc(s.file)}</div>
        <div class="muted small">${esc(s.platform)} audit log</div>
        <div class="kv"><span>${s.rows.toLocaleString()}</span> rows <span>${s.interviews.toLocaleString()}</span> interviews <span>${(s.rows / s.interviews).toFixed(1)}</span> rows each</div>
        <div class="chips-static">${s.columns.map((c) => `<code>${esc(c)}</code>`).join("")}</div></div>`).join("")}</div>
    </div>

    <div class="card"><h2>2. One interview, exactly as exported</h2>
      ${pickerHTML(id)}
      <p class="muted small">${plural(raw.rows.length, "row")} from <code>${esc(raw.file)}</code>. Read down: the interview opens, each question ends with its duration, a <code>jump</code> is the enumerator going back, and the interview closes.</p>
      ${table(raw.columns, raw.rows)}
      <h3>What each column means</h3>
      <dl class="glossary">${raw.columns.map((c) => `<dt><code>${esc(c)}</code></dt><dd>${esc(notes[c] || "")}</dd>`).join("")}</dl>
      <h3>Events in this batch</h3>
      <div class="bars">${b.sources.flatMap((s) => Object.entries(s.events).map(([name, n]) => ({ name, n, file: s.file })))
        .map((e) => `<div class="bar-row"><span class="mono">${esc(e.name)}</span><span class="bar-track"><span class="bar-fill" style="width:${(e.n / maxEvents * 100).toFixed(1)}%"></span></span><span class="muted">${e.n.toLocaleString()}${b.sources.length > 1 ? " · " + esc(e.file) : ""}</span></div>`).join("")}</div>
    </div>

    <div class="card"><h2>3. The two platforms side by side</h2>
      <p class="muted">Everything that could differ does. This is why the parsers exist.</p>
      <div class="table-wrap"><table><thead><tr><th></th><th>SurveyCTO</th><th>ODK</th></tr></thead><tbody>
        <tr><td>Interview ID</td><td><code>interview_id</code></td><td><code>instance_id</code></td></tr>
        <tr><td>Question</td><td><code>node</code></td><td><code>name</code></td></tr>
        <tr><td>Timestamps</td><td>Epoch milliseconds, <code>1672646401564</code></td><td>ISO 8601, <code>2023-01-02T08:00:00.779+00:00</code></td></tr>
        <tr><td>Duration</td><td>Given, <code>duration_ms</code></td><td>Not given; end minus start</td></tr>
        <tr><td>Event names</td><td><code>form-start</code>, <code>question-end</code>, <code>jump</code></td><td><code>form start</code>, <code>question-end</code>, <code>jump</code>, <code>end screen</code></td></tr>
      </tbody></table></div>
    </div>

    <div class="card"><h2>4. After parsing: one common shape</h2>
      <p class="muted">Both parsers produce the same six columns. Nothing after this step knows which platform a row came from, so one detector serves both. Bad rows are marked, not repaired or dropped.</p>
      <p class="muted small">The same interview, ${plural(raw.cir.length, "row")} after parsing:</p>
      ${table(raw.cir_columns, raw.cir)}
      <div class="grid-2"><div>
        <h3>How event names are normalised</h3>
        <div class="table-wrap"><table><thead><tr><th>Raw event</th><th>Becomes</th><th>Meaning</th></tr></thead><tbody>
          ${EVENT_MAP.map(([from, to, why]) => `<tr><td>${esc(from)}</td><td><code>${esc(to)}</code></td><td class="muted">${esc(why)}</td></tr>`).join("")}</tbody></table></div></div>
        <div><h3>What the pipeline sees: this interview in time</h3>${Charts.timeline({ rows: raw.cir, columns: raw.cir_columns })}
        <p class="muted small">Each bar is an event. Gaps between bars are time the log does not account for. The features in the next tab are measured from this.</p></div></div>
    </div>

    <div class="card"><h2>5. The labels file: validation only</h2>
      <p class="muted">These batches are synthetic, so every interview was generated with a known label. The detector never reads this file. It is joined to the detector's decisions afterwards, to score them. A real survey has no such file.</p>
      <p class="muted small"><code>${esc(b.ground_truth.path)}</code> · ${b.ground_truth.total.toLocaleString()} rows, first ${b.ground_truth.rows.length}:</p>
      ${table(b.ground_truth.columns, b.ground_truth.rows)}
    </div>`;
  bindPicker(box);
}

// ------------------------------------------------------------------- method ---

let methodToken = 0;
async function renderMethod() {
  const box = $("#view-method");
  if (!state.batch) return;
  const token = ++methodToken;
  const b = state.batch, id = state.selected || b.interviews[0].id;
  const feats = await getJSON(`data/features_${b.label}.json`);
  if (token !== methodToken) return;
  const iv = b.interviews.find((x) => x.id === id);
  const values = feats.rows[id] || [];
  const col = Object.fromEntries(feats.columns.map((c, i) => [c, i]));
  const fam = state.family || "Q";
  const index = state.index;
  const fired = new Set(iv.flags.map((f) => f.flag));
  const c = b.counts;
  const stages = [
    ["Ingest", "run_pipeline.py", `${b.raw_rows.toLocaleString()} raw rows read`],
    ["Parse", "src/parsers", `${b.interviews.length.toLocaleString()} interviews in one common shape`],
    ["Extract", "src/features", `${b.interviews.length.toLocaleString()} × 40 features`],
    ["Detect", "src/validation", `${c.flagged + c.review + c.dq} of ${c.total} need a look`],
    ["Report", "outputs and evaluation", `${b.files.length} files written`],
  ];
  const rulesBy = (kind) => index.rules.filter((r) => r.kind === kind);
  const ruleRow = (r) => `<tr${fired.has(r.flag) ? ' class="fired"' : ""}>
      <td><strong>${esc(r.name)}</strong><div class="mono muted">${esc(r.flag)}</div></td><td>${esc(r.rule)}</td>
      <td class="mono">${esc(r.uses.join(", "))}</td>
      <td>${fired.has(r.flag) ? `<span class="pill FLAGGED">Fired for ${esc(id)}</span>` : '<span class="muted">No</span>'}</td></tr>`;
  const ruleTable = (kind) => `<div class="table-wrap"><table><thead><tr><th>Flag</th><th>Rule</th><th>Features</th><th>${esc(id)}</th></tr></thead><tbody>${rulesBy(kind).map(ruleRow).join("")}</tbody></table></div>`;
  const hi = b.thresholds.flagged, lo = b.thresholds.review;
  const lane = (iv.dq ? "DQ" : iv.status);

  box.innerHTML = `
    <div class="card"><h2>The pipeline, one stage at a time</h2>
      <p class="muted">Each stage has one job and one module. The common shape after parsing is the only contract between the first two stages and everything after, so adding a platform means adding a parser and nothing else.</p>
      <ol class="stages">${stages.map(([name, module, note], i) => `<li><span class="stage-n">${i + 1}</span><strong>${name}</strong><span class="mono muted">${module}</span><span class="small">${esc(note)}</span></li>`).join("")}</ol>
    </div>

    <div class="card"><h2>Forty features in four families</h2>
      <p class="muted">A feature is one number that describes some aspect of how an interview was answered. Every feature is computed from the parsed rows, for every interview, the same way for both platforms.</p>
      ${pickerHTML(id)}
      <div class="chips" role="tablist" aria-label="Feature family">${index.families.map((f) =>
        `<button class="chip" data-family="${f.id}" aria-pressed="${f.id === fam}">${esc(f.name)}<span class="count">${index.catalogue.filter((x) => x.family === f.id).length}</span></button>`).join("")}</div>
      <p class="muted small">${esc(index.families.find((f) => f.id === fam).note)} The value shown is ${esc(id)}'s; the batch median is beside it. Q and S features are averaged over the interview.</p>
      <div class="table-wrap"><table><thead><tr><th>Feature</th><th>How it is measured</th><th>What it tells you</th><th class="num">${esc(id)}</th><th class="num">Batch median</th></tr></thead><tbody>
        ${index.catalogue.filter((f) => f.family === fam).map((f) => {
          const i = col[f.column];
          return `<tr><td><strong>${esc(f.id)}</strong><div class="mono muted">${esc(f.name)}</div></td><td>${code(f.definition)}</td><td class="muted">${esc(f.meaning)}</td>
            <td class="num">${i === undefined ? "n/a" : fmtFeature(f.column, values[i])}</td><td class="num muted">${i === undefined ? "n/a" : fmtFeature(f.column, feats.median[i])}</td></tr>`;
        }).join("")}</tbody></table></div>
    </div>

    <div class="card"><h2>The detector: named rules, a count, three lanes</h2>
      <p class="muted">There is no machine-learning model. A survey has no labelled field data to train one on, and a flag accuses a named person's work, so a supervisor must be able to see exactly which rules fired. Each rule is a named flag on a named feature. The score is how many fired.</p>
      <div class="zones" role="img" aria-label="Score zones">
        <div class="zone clean" style="flex:${lo}"><b>0 to ${lo - 1}</b>Clean</div>
        <div class="zone review" style="flex:${hi - lo}"><b>${lo} to ${hi - 1}</b>Review</div>
        <div class="zone flagged" style="flex:${Math.max(2, 4)}"><b>${hi} or more</b>Flagged</div>
      </div>
      <p class="muted small">${esc(id)} scored <strong>${iv.score}</strong> and sits in <span class="pill ${lane}">${LANE_NAME[lane]}</span>. A broken record goes to its own Data quality lane whatever its score, because device faults say nothing about the enumerator.</p>
      <h3>Behaviour rules <span class="muted small">· each fired rule adds one point</span></h3>${ruleTable("rule")}
      <h3>Statistical fences <span class="muted small">· together they add at most one point</span></h3>${ruleTable("iqr")}
      <h3>Data-quality rules <span class="muted small">· send the record to the Data quality lane</span></h3>${ruleTable("dq")}
    </div>

    <div class="card"><h2>What this batch's relative rules compare against</h2>
      <p class="muted">Most thresholds are relative to the batch itself, so the detector adapts to the instrument instead of assuming absolute times. The price is that most of the batch must be genuine. That is why the batch should pool every enumerator's uploads.</p>
      <div class="table-wrap"><table><thead><tr><th>Rule</th><th>Measured on</th><th>This batch</th><th>Fires when</th></tr></thead><tbody>
        ${b.batch_limits.map((r) => `<tr><td><strong>${esc(r.name)}</strong><div class="mono muted">${esc(r.flag)}</div></td><td>${esc(r.name.includes("fences") ? "Quartiles" : "Median")}</td><td>${esc(r.batch)}</td><td>${esc(r.limit)}</td></tr>`).join("")}</tbody></table></div>
    </div>`;
  bindPicker(box);
  box.querySelectorAll("[data-family]").forEach((el) => el.addEventListener("click", () => { state.family = el.dataset.family; renderMethod(); }));
}

// ------------------------------------------------------------------- charts ---

function renderCharts() {
  const box = $("#view-charts");
  if (!state.batch) return;
  const b = state.batch, h = b.histogram, p = b.profiles;
  const colorBy = state.colorBy || "lane";
  const laneOrder = ["CLEAN", "DQ", "REVIEW", "FLAGGED"];
  const labelOrder = ["normal", "dq_issue", "disengaged", "speeding", "fabricated"].filter((k) => h.by_label[k]);
  const thresholds = [{ at: b.thresholds.review, label: "Review" }, { at: b.thresholds.flagged, label: "Flagged" }].filter((t) => t.at < h.scores.length);
  const histogram = Charts.stackedColumns({
    xs: h.scores, groups: colorBy === "lane" ? h.by_lane : h.by_label, order: colorBy === "lane" ? laneOrder : labelOrder, thresholds,
  });
  const profileKeys = p.labels;
  const profileChart = Charts.lines({
    xs: b.questions.map((_, i) => i + 1),
    series: [...profileKeys.map((k) => ({ key: k, ys: p.series[k].map((v) => (v === null ? null : v / 1000)) })),
      { key: "var(--baseline)", name: "Whole batch median", dash: true, ys: b.batch_rt.map((v) => (v === null ? null : v / 1000)) }],
    xLabel: "Question, in instrument order", yLabel: "Response time", yFormat: (v) => v.toFixed(v < 10 ? 0 : 0) + " s", xEvery: 2,
  });
  const boxCharts = b.boxes.map((x) => {
    const f = (v) => (x.unit === "ms" ? secs(v) : x.unit === "pct" ? (v * 100).toFixed(0) + "%" : Number(v).toFixed(2));
    return `<div class="box-card"><h3>${esc(x.label)}</h3>${Charts.boxes({ groups: x.groups, order: ["normal", "disengaged", "speeding", "fabricated"], unit: x.unit, format: f })}</div>`;
  }).join("");
  const baseline = b.baselines.map((m) => `<div class="method">
      <div class="method-name">${esc(m.name)}</div>
      ${[["Precision", m.precision], ["Recall", m.recall], ["F1", m.f1]].map(([name, v]) => `<div class="bar-row"><span>${name}</span><span class="bar-track"><span class="bar-fill" style="width:${(v * 100).toFixed(1)}%"></span></span><span class="muted">${v.toFixed(3)}</span></div>`).join("")}
      <div class="muted small">${m.tp} found, ${m.fn} missed, ${m.fp} false alarms</div></div>`).join("");
  const env = state.index.envelope;
  const at = (difficulty, key) => env.filter((r) => r.difficulty === difficulty).map((r) => r[key]);
  const envChart = Charts.lines({
    xs: env.filter((r) => r.difficulty === "canonical").map((r) => r.prevalence * 100),
    series: [
      { key: "var(--series)", name: "Precision, easy data", ys: at("canonical", "precision") },
      { key: "var(--c-speeding)", name: "Recall, easy data", ys: at("canonical", "recall") },
      { key: "var(--series)", name: "Precision, harder data", dash: true, ys: at("stress", "precision") },
      { key: "var(--c-speeding)", name: "Recall, harder data", dash: true, ys: at("stress", "recall") },
      { key: "var(--c-fabricated)", name: "Fabrication recall, harder data", dash: true, ys: at("stress", "recall_fabricated") },
    ],
    yMax: 1, yTicks: [0, 0.25, 0.5, 0.75, 1], yFormat: (v) => v.toFixed(2), xFormat: (v) => v + "%",
    xLabel: "Share of the batch that is anomalous", yLabel: "Score", shade: { from: 5, label: "Anomalies are the majority" },
  });
  const byType = b.validation.by_type.map((r) => `<div class="bar-row"><span>${esc(r.anomaly_type.replace("dq_issue", "broken record"))}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${(r.detection_rate * 100).toFixed(1)}%"></span></span><span class="muted">${r.detected} of ${r.total}</span></div>`).join("");
  const duration = b.baselines.find((m) => m.name.startsWith("Duration"));
  const full = b.baselines[0];

  box.innerHTML = `
    <div class="card"><div class="card-head"><h2>Where the scores fall</h2>
      <div class="chips" role="group" aria-label="Colour by">
        <button class="chip" data-color="lane" aria-pressed="${colorBy === "lane"}">By queue lane</button>
        <button class="chip" data-color="label" aria-pressed="${colorBy === "label"}">By true label</button></div></div>
      ${histogram}
      <p class="muted small"><strong>What to look for.</strong> Genuine interviews pile up at low scores; fabricated, speeding and disengaged ones sit higher. Colouring by true label (possible only because the data is synthetic) shows how cleanly the two groups separate. The dashed lines are the review and flagged thresholds.</p></div>

    <div class="card"><h2>What the interview profiles look like</h2>
      ${profileChart}
      <p class="muted small"><strong>What to look for.</strong> Mean response time on each question, by true profile (${profileKeys.map((k) => `${p.counts[k]} ${Charts.NAME[k].toLowerCase()}`).join(", ")}). Genuine interviews rise and fall with how hard each question is. Fabricated and speeding interviews are flat: the same time whatever the question. Flatness is what entropy and the coefficient of variation measure.</p></div>

    <div class="card"><h2>Which features separate them</h2>
      <div class="box-grid">${boxCharts}</div>
      <p class="muted small"><strong>What to look for.</strong> Each box spans the middle half of that profile's interviews, the line inside is the median, the thin line reaches the typical extremes. A feature is useful when the boxes barely overlap. Entropy and the coefficient of variation put speeding and fabricated interviews far from genuine ones. Disengaged interviews are harder: they take a similar total time, and what gives them away is how they navigate and pause.</p></div>

    <div class="card"><h2>The detector against the checks field teams already run</h2>
      <div class="methods">${baseline}</div>
      <p class="muted small"><strong>What to look for.</strong> On this batch the duration check finds ${duration.tp} of ${duration.tp + duration.fn} anomalies and the full detector finds ${full.tp}. The duration check flags only interviews outside the fences of the batch's own spread, which here run from ${secs(duration.fences[0])} to ${secs(duration.fences[1])}${duration.fences[0] < 0 ? ". The lower fence is below zero, so no interview can ever be flagged as too short" : ""}. The report measures the same on 400 stress-test anomalies, where the duration check finds none.</p></div>

    <div class="card"><h2>Where the method stops working</h2>
      ${envChart}
      <p class="muted small"><strong>What to look for.</strong> Both targets (precision 0.80, recall 0.75) hold up to half the batch being anomalous. Past that, the batch median is itself an anomalous interview, so the relative thresholds move and recall falls. This is why a batch must pool every enumerator: one enumerator who fabricates their whole caseload, analysed alone, looks like a batch that is almost all anomalous. From the report's prevalence sweep, 500 interviews per run.</p></div>

    <div class="card"><h2>Caught, by type of problem</h2><div class="bars">${byType}</div>
      <p class="muted small">Speeding is caught in every case. Mild fabrication is the weakest type, as the harder batch shows.</p></div>

    ${state.index.notebook ? `<div class="card"><h2>More plots</h2><p>The audit notebook adds the score distribution, a feature correlation heatmap, anomaly score against duration, section-level boxplots and a pairplot.</p><p><a href="notebook.html">Open the executed notebook</a></p></div>` : ""}`;
  box.querySelectorAll("[data-color]").forEach((el) => el.addEventListener("click", () => { state.colorBy = el.dataset.color; renderCharts(); }));
}

function refreshViews() {
  if (!$("#view-data").hidden) renderData();
  if (!$("#view-method").hidden) renderMethod();
  if (!$("#view-charts").hidden) renderCharts();
}
