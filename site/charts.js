// Small SVG chart helpers. Each returns an SVG string and uses CSS variables for
// colour, so charts follow the light and dark theme. No libraries.
"use strict";

const Charts = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const COLOR = {
    normal: "var(--c-normal)", fabricated: "var(--c-fabricated)", speeding: "var(--c-speeding)",
    disengaged: "var(--c-disengaged)", dq_issue: "var(--c-dq)",
    FLAGGED: "var(--flagged)", REVIEW: "var(--review)", DQ: "var(--dq)", CLEAN: "var(--clean)",
  };
  const NAME = { normal: "Genuine", fabricated: "Fabricated", speeding: "Speeding", disengaged: "Disengaged",
    dq_issue: "Broken record", FLAGGED: "Flagged", REVIEW: "Review", DQ: "Data quality", CLEAN: "Clean" };

  const nice = (max) => {
    if (max <= 0) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(max)));
    const n = max / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
  };
  const legend = (items, fill = false) => `<div class="legend${fill ? " fill" : ""}">${items.map((it) => {
    const o = typeof it === "string" ? { key: it } : it;
    return `<span class="${o.dash ? "dashed" : ""}" style="--swatch:${COLOR[o.key] || o.key}"><i></i>${esc(o.name || NAME[o.key] || o.key)}</span>`;
  }).join("")}</div>`;

  // Stacked columns: one column per score, split by group.
  function stackedColumns({ xs, groups, order, thresholds = [], xLabel = "Score", height = 230 }) {
    const W = 620, H = height, L = 44, R = 12, T = 14, B = 38;
    const totals = xs.map((_, i) => order.reduce((a, g) => a + (groups[g]?.[i] || 0), 0));
    const top = nice(Math.max(...totals, 1));
    const bw = (W - L - R) / xs.length;
    const y = (v) => T + (H - T - B) * (1 - v / top);
    const ticks = [0, top / 2, top];
    let bars = "";
    xs.forEach((x, i) => {
      let acc = 0;
      order.forEach((g) => {
        const v = groups[g]?.[i] || 0;
        if (!v) return;
        bars += `<rect x="${L + i * bw + 2}" y="${y(acc + v)}" width="${Math.max(1, bw - 4)}" height="${y(acc) - y(acc + v)}" fill="${COLOR[g]}"><title>Score ${x}: ${v} ${esc(NAME[g] || g)}</title></rect>`;
        acc += v;
      });
      bars += `<text x="${L + i * bw + bw / 2}" y="${H - 20}" text-anchor="middle">${x}</text>`;
    });
    const lines = thresholds.map((t) => `<line class="thresh" x1="${L + t.at * bw}" x2="${L + t.at * bw}" y1="${T}" y2="${H - B}"/>
      <text x="${L + t.at * bw + 4}" y="${T + 10}">${esc(t.label)}</text>`).join("");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Interviews by score">
      ${ticks.map((t) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${t}</text>`).join("")}
      ${bars}${lines}<text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">${esc(xLabel)}</text></svg>
      ${legend(order, true)}`;
  }

  // Lines over a shared x axis.
  function lines({ xs, series, yMax, yTicks, xLabel, yLabel, xFormat = String, yFormat = String, height = 240, xEvery = 1, shade = null }) {
    const W = 620, H = height, L = 48, R = 12, T = 12, B = 40;
    const vals = series.flatMap((s) => s.ys).filter((v) => v !== null && v !== undefined);
    const top = yMax ?? nice(Math.max(...vals, 1));
    const x = (i) => L + (xs.length === 1 ? 0 : (i * (W - L - R)) / (xs.length - 1));
    const y = (v) => T + (H - T - B) * (1 - v / top);
    const ticks = yTicks ?? [0, top / 2, top];
    const path = (ys) => ys.map((v, i) => (v === null || v === undefined ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(" ");
    const band = shade ? `<rect class="shade" x="${x(shade.from)}" y="${T}" width="${x(xs.length - 1) - x(shade.from)}" height="${H - T - B}"/><text x="${x(shade.from) + 6}" y="${T + 12}">${esc(shade.label)}</text>` : "";
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(yLabel)} by ${esc(xLabel)}">
      ${band}
      ${ticks.map((t) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${esc(yFormat(t))}</text>`).join("")}
      ${xs.map((v, i) => (i % xEvery === 0 || i === xs.length - 1) ? `<text x="${x(i)}" y="${H - 22}" text-anchor="middle">${esc(xFormat(v))}</text>` : "").join("")}
      ${series.map((s) => `<polyline class="series" style="stroke:${COLOR[s.key] || s.key};${s.dash ? "stroke-dasharray:5 4;" : ""}${s.faint ? "opacity:.55;" : ""}" points="${path(s.ys)}"/>`).join("")}
      <text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">${esc(xLabel)}</text></svg>
      ${legend(series.map((s) => ({ key: s.key, name: s.name, dash: s.dash })))}`;
  }

  // Box plots, one box per group, drawn horizontally so long labels fit.
  function boxes({ groups, order, unit, format }) {
    const W = 300, rowH = 30, L = 82, R = 10, T = 6, B = 20;
    const present = order.filter((g) => groups[g]);
    if (!present.length) return `<p class="muted small">No data.</p>`;
    const H = T + present.length * rowH + B;
    const lo = Math.min(...present.map((g) => groups[g].lo)), hi = Math.max(...present.map((g) => groups[g].hi));
    const pad = (hi - lo) * 0.04 || 1;
    const x = (v) => L + ((v - (lo - pad)) / ((hi + pad) - (lo - pad))) * (W - L - R);
    const ticks = [lo, (lo + hi) / 2, hi];
    return `<svg class="chart small-chart" viewBox="0 0 ${W} ${H}" role="img">
      ${ticks.map((t) => `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${T}" y2="${H - B}"/><text x="${x(t)}" y="${H - 6}" text-anchor="middle">${esc(format(t))}</text>`).join("")}
      ${present.map((g, i) => {
        const b = groups[g], cy = T + i * rowH + rowH / 2;
        return `<g><title>${esc(NAME[g])}: median ${esc(format(b.med))}, middle half ${esc(format(b.q1))} to ${esc(format(b.q3))}, ${b.n} interviews</title>
          <text x="${L - 6}" y="${cy + 4}" text-anchor="end">${esc(NAME[g])}</text>
          <line class="whisker" x1="${x(b.lo)}" x2="${x(b.hi)}" y1="${cy}" y2="${cy}"/>
          <rect x="${x(b.q1)}" y="${cy - 8}" width="${Math.max(2, x(b.q3) - x(b.q1))}" height="16" rx="3" fill="${COLOR[g]}" fill-opacity=".55" stroke="${COLOR[g]}"/>
          <line x1="${x(b.med)}" x2="${x(b.med)}" y1="${cy - 8}" y2="${cy + 8}" stroke="var(--ink)" stroke-width="2"/></g>`;
      }).join("")}</svg>`;
  }

  // The events of one interview on a time line, from its parsed rows.
  function timeline({ rows, columns, jumpWord = "jump" }) {
    const idx = Object.fromEntries(columns.map((c, i) => [c, i]));
    const ev = rows.map((r) => ({ type: r[idx.event_type], name: r[idx.field_name], s: r[idx.start_ms], e: r[idx.end_ms] }));
    if (!ev.length) return `<p class="muted small">No events.</p>`;
    const t0 = Math.min(...ev.map((x) => x.s)), t1 = Math.max(...ev.map((x) => x.e));
    const W = 620, H = 120, L = 10, R = 10, span = Math.max(1, t1 - t0);
    const x = (t) => L + ((t - t0) / span) * (W - L - R);
    const kind = (t) => (t === "jump" ? "jump" : t === "form_start" || t === "form_end" ? "form" : t.includes("constraint") ? "constraint" : "answer");
    const secs = span / 1000;
    const marks = [0, 0.25, 0.5, 0.75, 1].map((f) => `<line class="grid" x1="${L + f * (W - L - R)}" x2="${L + f * (W - L - R)}" y1="14" y2="82"/>
      <text x="${L + f * (W - L - R)}" y="98" text-anchor="${f === 0 ? "start" : f === 1 ? "end" : "middle"}">${(secs * f).toFixed(secs > 60 ? 0 : 1)} s</text>`).join("");
    const bars = ev.map((v) => {
      const k = kind(v.type), x0 = x(v.s), w = Math.max(1.5, x(v.e) - x(v.s));
      const y0 = k === "jump" ? 20 : k === "answer" ? 34 : 50;
      const h = k === "jump" ? 56 : k === "answer" ? 30 : 22;
      return `<rect class="ev ev-${k}" x="${x0}" y="${y0}" width="${w}" height="${h}" rx="1.5"><title>${esc(v.type)}${v.name && v.name !== "unknown_field" ? " · " + esc(v.name) : ""}: ${(((v.e - v.s) || 0) / 1000).toFixed(1)} s</title></rect>`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Events in time order">${marks}${bars}</svg>
      <div class="legend"><span style="--swatch:var(--series)"><i></i>Answer time</span><span style="--swatch:var(--flagged)"><i></i>Back or jump</span><span style="--swatch:var(--baseline)"><i></i>Form start and end</span></div>`;
  }

  return { stackedColumns, lines, boxes, timeline, COLOR, NAME, legend };
})();
