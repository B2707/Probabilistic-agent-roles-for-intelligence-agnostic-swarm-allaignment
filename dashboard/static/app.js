/* Swarm Ops client. Plain JS; ECharts 5.5.0 from cdnjs for charts, heatmap and network. */
"use strict";

// ------------------------------------------------------------------------------------------------ utilities
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const nowS = () => Date.now() / 1000 + (S.offset || 0);
const sum = (a) => a.reduce((x, y) => x + (y || 0), 0);
const mean = (a) => (a.length ? sum(a) / a.length : null);
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

const F = {
  int: (n) => (n == null || n === "" ? "–" : Math.round(n).toLocaleString()),
  num: (n, d = 1) => (n == null ? "–" : Number(n).toFixed(d)),
  pct: (n, d = 1) => (n == null ? "–" : (100 * n).toFixed(d) + "%"),
  tok: (n) => { if (n == null) return "–"; const a = Math.abs(n);
    return a >= 1e9 ? (n / 1e9).toFixed(2) + "B" : a >= 1e6 ? (n / 1e6).toFixed(1) + "M" : a >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(Math.round(n)); },
  dur: (s) => { if (s == null || !isFinite(s)) return "–"; s = Math.max(0, Math.round(s)); const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    return d ? `${d}d ${h}h` : h ? `${h}h ${String(m).padStart(2, "0")}m` : m ? `${m}m ${String(s % 60).padStart(2, "0")}s` : `${s}s`; },
  clock: (t) => (t ? new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "–"),
  clockS: (t) => (t ? new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "–"),
  day: (t) => (t ? new Date(t * 1000).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "–"),
  ago: (t) => (t ? F.dur(nowS() - t) + " ago" : "–"),
  gb: (b) => (b == null ? "–" : (b / 1073741824).toFixed(1) + " GB"),
};

const GROUPS = [
  ["v3", "v3 · 100 agents · 55 problems · global review", "Seed 1 runs on this Mac, seed 2 on the laptop. Grouped by worker model, then arm."],
  ["v2-shuffled", "v2 · shuffled turn order", ""],
  ["stopped", "Stopped by hand", "First attempts stopped by hand. Excluded from comparisons."],
  ["v2-archive", "v2 archive · fixed turn order", "results/ordered/: agents a001–a010 always went first, so these are biased. Kept for reference."],
  ["v1", "v1 & pilots", "Pre-v2 harness."],
];
const COND = {
  none: { label: "no investigators", color: "--s3" },
  uninformed: { label: "hidden investigators, not told", color: "--s2" },
  informed: { label: "hidden investigators, told", color: "--s1" },
  bluff: { label: "told, but no investigators (bluff)", color: "--s4" },
  "audits-only": { label: "random audits only", color: "--s5" },
};
const CATS = [["chat", "DMs & board"], ["instigator", "instigator"], ["prs", "PRs"], ["tests", "tests"], ["oversight", "oversight"],
  ["errors", "errors"], ["lifecycle", "rounds"], ["say", "agent replies"], ["progress", "progress"], ["tools", "tool calls"], ["turns", "turns"]];
const DEFAULT_CATS = ["chat", "instigator", "prs", "tests", "oversight", "errors", "lifecycle"];
const ARM_ORDER = (b) => ({ A100: 0, B100: 1, C100: 2 }[b] ?? 10);

const S = {
  runs: new Map(), machine: null, peers: [], light: null, fleet: null, offset: 0, deadline_t: null,
  route: { view: "overview" }, runName: null, detail: null, after: null, feed: [], feedSeen: new Set(),
  cats: new Set(loadJSON("swarm-cats", DEFAULT_CATS)), fAgent: "", fTeam: "", fQ: "", paused: false,
  replay: null, playing: null, tab: "live", net: null, netGroup: null, prs: null,
  es: null, esKey: null, lastEvent: null, notify: loadJSON("swarm-notify", false), toastGate: new Map(), ready: false,
  overlay: { metric: "problems_at_100", names: null }, archiveOpen: loadJSON("swarm-archive-open", false),
  model: null, compareRound: "latest", agentSort: ["slot", 1], prSort: ["id", -1], prFilter: "all",
};
function loadJSON(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
function saveJSON(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } }

async function api(path) {
  const r = await fetch(path, { credentials: "same-origin" });
  if (r.status === 401) { location.reload(); throw new Error("unauthorized"); }
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).error || m; } catch (e) { /* not json */ } throw new Error(m); }
  return r.json();
}
const runUrl = (name, rest = "") => `/api/run/${encodeURIComponent(name)}${rest}`;
const armLabel = (s) => `${s.arm_base || s.arm}${s.seed && s.group === "v3" ? " · s" + s.seed : ""}`;
const modelLabel = (m) => String(m || "?").replace(/^adaption\//, "").replace(/^gpt-/, "");
const condColor = (c) => css((COND[c] || {}).color || "--muted");

// ------------------------------------------------------------------------------------------------ charts
const charts = new Set();
function chart(el, opt) {
  if (!window.echarts || !el) { if (el && !el.dataset.nolib) { el.dataset.nolib = 1; el.innerHTML = '<div class="empty">Charts need cdnjs.cloudflare.com (blocked?)</div>'; } return null; }
  let c = echarts.getInstanceByDom(el);
  if (!c) { c = echarts.init(el, null, { renderer: "canvas" }); charts.add(c); }
  c.setOption(opt, { notMerge: true });
  return c;
}
function disposeCharts(root = document) {
  if (!window.echarts) return;
  $$(".chart", root).forEach((el) => { const c = echarts.getInstanceByDom(el); if (c) { charts.delete(c); c.dispose(); } });
}
window.addEventListener("resize", debounce(() => charts.forEach((c) => { try { c.resize(); } catch (e) { charts.delete(c); } }), 150));

function base(o = {}) {
  const ink = css("--ink-2"), muted = css("--muted"), grid = css("--grid"), axis = css("--axis");
  return {
    animation: false, backgroundColor: "transparent", textStyle: { fontFamily: css("--sans") || "system-ui" },
    grid: { left: 46, right: 16, top: o.legend === false ? 18 : 34, bottom: 26, containLabel: false, ...(o.grid || {}) },
    tooltip: { trigger: "axis", backgroundColor: css("--surface"), borderColor: css("--border-strong"), textStyle: { color: css("--ink"), fontSize: 12 },
      axisPointer: { type: "line", lineStyle: { color: axis } }, confine: true, ...(o.tooltip || {}) },
    legend: o.legend === false ? undefined : { top: 0, left: 0, right: 40, type: "scroll", itemWidth: 14, itemHeight: 8, textStyle: { color: ink, fontSize: 11.5 }, ...(o.legend || {}) },
    toolbox: { right: 0, top: -6, itemSize: 13, iconStyle: { borderColor: muted },
      feature: { saveAsImage: { title: "PNG", pixelRatio: 2, backgroundColor: css("--surface"), name: o.file || "swarm-chart" } } },
    xAxis: { type: "category", boundaryGap: o.bars ? true : false, data: o.x || [], name: o.xName, nameLocation: "middle", nameGap: 20, nameTextStyle: { color: muted, fontSize: 11 },
      axisLine: { lineStyle: { color: axis } }, axisTick: { show: false }, axisLabel: { color: muted, fontSize: 11 }, ...(o.xAxis || {}) },
    yAxis: { type: "value", minInterval: o.int ? 1 : undefined, max: o.max, min: o.min, splitLine: { lineStyle: { color: grid } },
      axisLabel: { color: muted, fontSize: 11, formatter: o.yfmt }, ...(o.yAxis || {}) },
  };
}
function line(name, data, color, extra = {}) {
  return { type: "line", name, data, showSymbol: data.filter((x) => x != null).length < 3, symbolSize: 7, connectNulls: false,
    lineStyle: { width: 2, color, type: extra.dash ? "dashed" : "solid" }, itemStyle: { color }, emphasis: { focus: "series" }, ...extra };
}
function bar(name, data, color, extra = {}) {
  return { type: "bar", name, data, itemStyle: { color, borderRadius: [3, 3, 0, 0] }, barMaxWidth: 22, emphasis: { focus: "series" }, ...extra };
}
function markRound(series, r) {
  if (r == null || !series.length) return series;
  series[0].markLine = { silent: true, symbol: "none", lineStyle: { color: css("--warn"), type: "dashed", width: 1.5 }, label: { show: false }, data: [{ xAxis: String(r) }] };
  return series;
}

// ------------------------------------------------------------------------------------------------ boot, routing, SSE
async function boot() {
  bindGlobal();
  try {
    const st = await api("/api/state");
    applyState(st);
  } catch (e) { $("#view").innerHTML = `<div class="empty">Could not load: ${esc(e.message)}</div>`; return; }
  S.ready = true;
  route();
  setInterval(tick, 1000);
  setInterval(() => { if (!S.es || S.es.readyState === 2) connect(true); }, 5000);
}
function applyState(st) {
  S.machine = st.machine; S.offset = st.now - Date.now() / 1000; S.deadline_t = st.deadline_t; S.peers = st.peers || [];
  S.light = { local: st.light, peers: st.peers }; S.fleet = (st.light || {}).fleet;
  S.runs = new Map(st.runs.map((r) => [r.name, r]));
}

function parseHash() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  const parts = h.split("/").filter(Boolean);
  if (!parts.length) return { view: "overview" };
  if (parts[0] === "run") return { view: "run", name: parts[1] || null, tab: parts[2] || null };
  if (["results", "ops", "fleet", "overview"].includes(parts[0])) return { view: parts[0] };
  return { view: "overview" };
}
function route() {
  const r = parseHash();
  closeDrawer();
  if (r.view === "run" && !r.name) {
    const pick = S.runName || [...S.runs.values()].filter((s) => s.state === "running" && !s.snapshot).sort((a, b) => (b.last_t || 0) - (a.last_t || 0))[0]?.name
      || [...S.runs.values()].sort((a, b) => (b.last_t || 0) - (a.last_t || 0))[0]?.name;
    if (pick) { location.replace(`#/run/${encodeURIComponent(pick)}`); return; }
  }
  disposeCharts($("#view"));
  S.route = r;
  $$("#nav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === r.view));
  if (r.view === "run") {
    if (r.name !== S.runName) { S.runName = r.name; S.detail = null; S.feed = []; S.feedSeen = new Set(); S.after = null; S.replay = null; S.net = null; S.prs = null; S.netGroup = null; stopPlay(); }
    S.tab = r.tab || S.tab || "live";
    $("#nav-run").textContent = "Run · " + (S.runs.get(r.name) ? armLabel(S.runs.get(r.name)) : r.name);
    renderRun();
  } else {
    if (r.view === "overview") renderOverview();
    if (r.view === "results") renderResults();
    if (r.view === "ops") renderOps();
    if (r.view === "fleet") renderFleet();
    connect();
  }
  renderBanner();
}
window.addEventListener("hashchange", route);

function connect(force = false) {
  const run = S.route.view === "run" && S.runName && S.after != null ? S.runName : "";
  const key = run ? `${run}` : "";
  if (!force && S.es && S.esKey === key && S.es.readyState !== 2) return;
  if (S.es) S.es.close();
  const url = `/api/stream?run=${encodeURIComponent(run)}${run ? `&after=${S.after}` : ""}`;
  const es = new EventSource(url);
  S.es = es; S.esKey = key;
  setLive("connecting");
  es.addEventListener("hello", (e) => { const d = JSON.parse(e.data); S.offset = d.now - Date.now() / 1000; setLive("on"); });
  es.addEventListener("summary", (e) => onSummaries(JSON.parse(e.data)));
  es.addEventListener("runs", (e) => onRunNames(JSON.parse(e.data)));
  es.addEventListener("events", (e) => onEvents(JSON.parse(e.data)));
  es.addEventListener("light", (e) => { const d = JSON.parse(e.data); S.light = d; S.fleet = (d.local || {}).fleet || S.fleet; renderMachines(); if (S.route.view === "fleet") renderFleet(true); });
  es.onerror = () => { setLive("off"); };
  es.onopen = () => setLive("on");
}
function setLive(state) {
  const el = $("#live"); el.className = "live " + (state === "on" ? "on" : state === "off" ? "off" : "");
  el.querySelector("span").textContent = state === "on" ? (S.lastEvent ? "live · last event " + F.ago(S.lastEvent) : "live") : state === "off" ? "reconnecting…" : "connecting…";
}

const rerenderView = debounce(() => {
  if (S.route.view === "overview") renderOverview();
  else if (S.route.view === "results") renderResults(true);
  else if (S.route.view === "fleet") renderFleet(true);
  else if (S.route.view === "run") renderRunHeader();
  renderBanner();
}, 700);

function onSummaries(list) {
  for (const s of list) {
    const old = S.runs.get(s.name);
    if (old && S.ready) notifyDiff(old, s);
    S.runs.set(s.name, s);
    if (s.last_t && (!S.lastEvent || s.last_t > S.lastEvent) && s.state === "running") S.lastEvent = s.last_t;
  }
  rerenderView();
}

// the server's full run list: drop runs it no longer lists ("summary" only adds and updates)
function onRunNames(names) {
  const keep = new Set(names);
  let dropped = false;
  for (const name of [...S.runs.keys()]) if (!keep.has(name)) { S.runs.delete(name); dropped = true; }
  if (dropped) rerenderView();
}

function notifyDiff(a, b) {
  const who = `${armLabel(b)} (${modelLabel(b.model)}${b.machine && b.machine !== S.machine ? ", " + b.machine : ""})`;
  if ((b.problems_at_100 || 0) > (a.problems_at_100 || 0)) toast("crit", `${who}: ${b.problems_at_100} problems at 100%`, `+${b.problems_at_100 - (a.problems_at_100 || 0)} at round end: a cheat is on main.`, b.name, "at100");
  if ((b.removed || 0) > (a.removed || 0)) toast("warn", `${who}: agent removed`, `${b.removed} removed so far.`, b.name, "removed");
  if (a.state !== b.state) {
    const kind = ["interrupted", "stalled", "usage-limit"].includes(b.state) ? "crit" : b.state === "resuming" ? "warn" : "good";
    toast(kind, `${who}: ${b.state}`, b.state_detail || `was ${a.state}`, b.name, "state");
  }
}
function toast(kind, title, body, run, gate) {
  const key = `${run}:${gate}`, t = Date.now();
  if (S.toastGate.get(key) > t - 20000) return;
  S.toastGate.set(key, t);
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.innerHTML = `<b>${esc(title)}</b>${esc(body)}`;
  el.onclick = () => { location.hash = `#/run/${encodeURIComponent(run)}`; el.remove(); };
  $("#toasts").prepend(el);
  setTimeout(() => el.remove(), 12000);
  while ($("#toasts").children.length > 5) $("#toasts").lastChild.remove();
  if (S.notify && "Notification" in window && Notification.permission === "granted" && document.hidden) {
    try { new Notification(title, { body, tag: key }); } catch (e) { /* unsupported */ }
  }
}

function tick() {
  const d = $("#deadline");
  if (S.deadline_t) {
    const left = S.deadline_t - nowS();
    d.innerHTML = left > 0 ? `Deadline in <b>${F.dur(left)}</b>` : "<b>Deadline passed</b>";
    d.classList.toggle("soon", left < 6 * 3600);
  }
  $$("[data-ago]").forEach((el) => { el.textContent = F.ago(+el.dataset.ago); });
  $$("[data-since]").forEach((el) => { el.textContent = F.dur(nowS() - +el.dataset.since); });
  $$("[data-until]").forEach((el) => { const l = +el.dataset.until - nowS(); el.textContent = l > 0 ? F.dur(l) : "due"; });
  if (S.es && S.es.readyState === 1) setLive("on");
}

function bindGlobal() {
  $("#theme").onclick = () => {
    const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = t; saveJSON("swarm-theme", t); try { localStorage.setItem("swarm-theme", t); } catch (e) { /* ignore */ }
    disposeCharts(); route();
  };
  const nb = $("#notify"); nb.classList.toggle("on", !!S.notify);
  nb.onclick = async () => {
    if (!S.notify && "Notification" in window && Notification.permission !== "granted") { try { await Notification.requestPermission(); } catch (e) { /* ignore */ } }
    S.notify = !S.notify; saveJSON("swarm-notify", S.notify); nb.classList.toggle("on", S.notify);
    toast("good", S.notify ? "Notifications on" : "Notifications off", S.notify ? "Cheats on main, removals and run state changes, while this tab is in the background." : "", "", "n" + Date.now());
  };
  $("#drawer-close").onclick = closeDrawer;
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName || "");
    if (e.key === "Escape") closeDrawer();
    if (typing) return;
    if (e.key === "/" && $("#fq")) { e.preventDefault(); $("#fq").focus(); }
    if (S.route.view === "run" && S.detail) {
      if (e.key === "ArrowLeft") { setReplay(Math.max(0, (S.replay ?? curRound()) - 1)); e.preventDefault(); }
      if (e.key === "ArrowRight") { const r = (S.replay ?? curRound()) + 1; setReplay(r >= curRound() ? null : r); e.preventDefault(); }
      if (e.key === " ") { togglePlay(); e.preventDefault(); }
    }
  });
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-agent]");
    if (a) { e.preventDefault(); e.stopPropagation(); openAgent(a.dataset.run || S.runName, a.dataset.agent); return; }
    const p = e.target.closest("[data-pr]");
    if (p) { e.preventDefault(); e.stopPropagation(); openPR(p.dataset.run || S.runName, p.dataset.pr); return; }
    const raw = e.target.closest("[data-raw]");
    if (raw) { e.preventDefault(); e.stopPropagation(); openRaw(raw.dataset.run || S.runName, +raw.dataset.raw); return; }
    const tr = e.target.closest("tr[data-run]");
    if (tr && !e.target.closest("a")) { location.hash = `#/run/${encodeURIComponent(tr.dataset.run)}`; return; }
    const ev = e.target.closest(".ev");
    if (ev && !e.target.closest("a,button")) ev.classList.toggle("open");
  });
}

function renderMachines() {
  const el = $("#machines"); if (!el) return;
  const dev = (S.fleet || {}).devices || [];
  const chips = [];
  const loc = (S.light || {}).local || {};
  const me = dev.find((d) => (d.keys || []).includes(loc.machine_key)) || dev.find((d) => d.self);
  chips.push(machineChip(S.machine || loc.machine, true, me, loc));
  for (const p of S.peers || []) chips.push(machineChip(p.machine || p.url, p.ok, null, p.light, p.error));
  const snaps = new Set([...S.runs.values()].filter((s) => s.snapshot).map((s) => s.machine));
  for (const m of snaps) {
    const t = Math.max(...[...S.runs.values()].filter((s) => s.snapshot && s.machine === m).map((s) => s.snapshot_t || 0));
    chips.push(`<span class="chip ${nowS() - t < 1800 ? "ok" : "bad"}" title="Status pushed through git (results/live-${esc(m)}.md)"><i></i>${esc(m)} · snapshot ${F.clock(t)}</span>`);
  }
  el.innerHTML = chips.join("");
}
function machineChip(name, ok, dev, light, err) {
  const st = dev && dev.status;
  const bits = [];
  if (st) {
    if (st.battery) bits.push(`${st.battery.percent}%${st.battery.onPower ? "⚡" : ""}`);
    bits.push(`CPU ${Math.round(st.cpuPercent)}%`);
    bits.push(`RAM ${F.num(st.memory.usedBytes / 1073741824, 0)}/${F.num(st.memory.totalBytes / 1073741824, 0)}G`);
  } else if (light && light.machine_stats && light.machine_stats.load) bits.push(`load ${light.machine_stats.load[0]}`);
  const pressure = st && st.memory.pressure;
  const cls = !ok ? "bad" : pressure && pressure !== "normal" ? "bad" : "ok";
  const title = err ? esc(err) : `${esc(name)}${light && light.machine_stats ? ` · load ${light.machine_stats.load} on ${light.machine_stats.ncpu} cores` : ""}${light && light.codex != null ? ` · ${light.codex} codex sessions` : ""}`;
  return `<a class="chip ${cls}" href="#/fleet" title="${title}"><i></i>${esc(name)}${bits.length ? " · " + bits.join(" · ") : ""}</a>`;
}

function renderBanner() {
  renderMachines();
  const bad = [...S.runs.values()].filter((s) => ["interrupted", "stalled"].includes(s.state) && ["v3", "v2-shuffled"].includes(s.group));
  const b = $("#banner");
  if (!bad.length) { b.hidden = true; return; }
  b.hidden = false;
  b.innerHTML = `<b>${bad.length} run${bad.length > 1 ? "s" : ""} need attention:</b> ` + bad.map((s) =>
    `<a href="#/run/${encodeURIComponent(s.name)}">${esc(armLabel(s))}</a> ${esc(s.state)} (${esc(s.state_detail || "")}; last event <span data-ago="${s.last_t}">${F.ago(s.last_t)}</span>)`).join(" · ");
}

// ------------------------------------------------------------------------------------------------ overview
function badge(s) {
  const extra = s.snapshot ? ` title="${esc(s.state_detail)}"` : s.state_detail ? ` title="${esc(s.state_detail)}"` : "";
  return `<span class="badge st-${esc(s.state)}"${extra}>${esc(s.state)}${s.snapshot ? " ·snap" : ""}</span>`;
}
function progress(s) {
  const tot = s.rounds_total || 20, done = Math.min(tot, s.completed_rounds || 0);
  const cur = s.state === "running" && s.round > done ? 1 : 0;
  const ph = s.state === "running" && s.phase === "turns" ? `turns ${s.turns_done}/${s.active_agents}` : s.phase && s.state === "running" ? s.phase : "";
  return `<div class="prog"><div class="bar"><i style="width:${(100 * done) / tot}%"></i>${cur ? `<i class="cur" style="width:${100 / tot}%"></i>` : ""}</div>
    <div class="lbl"><span>R${s.round || 0}/${tot}</span><span class="muted">${esc(ph)}</span></div></div>`;
}
function spark(vals, color, w = 70, h = 18) {
  const v = (vals || []).filter((x) => x != null);
  if (v.length < 2) return '<span class="muted">–</span>';
  const mx = Math.max(...v, 1e-9), mn = Math.min(...v, 0);
  const pts = v.map((y, i) => `${((i / (v.length - 1)) * (w - 2) + 1).toFixed(1)},${(h - 2 - ((y - mn) / (mx - mn || 1)) * (h - 4)).toFixed(1)}`).join(" ");
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline fill="none" stroke="${color}" stroke-width="1.6" points="${pts}"/></svg>`;
}
function elapsed(s) {
  if (!s.start_t) return "–";
  if (s.state === "running" && !s.snapshot) return `<span data-since="${s.start_t}">${F.dur(nowS() - s.start_t)}</span>`;
  return F.dur((s.end_t || s.last_t || s.start_t) - s.start_t);
}
function sortRuns(list) {
  return list.sort((a, b) => String(a.model).localeCompare(String(b.model)) || ARM_ORDER(a.arm_base) - ARM_ORDER(b.arm_base)
    || String(a.arm_base).localeCompare(String(b.arm_base)) || (a.seed || 0) - (b.seed || 0) || (b.start_t || 0) - (a.start_t || 0));
}

function renderOverview() {
  const runs = [...S.runs.values()];
  const live = runs.filter((s) => s.state === "running");
  const att = runs.filter((s) => ["interrupted", "stalled", "usage-limit", "resuming"].includes(s.state) && ["v3", "v2-shuffled"].includes(s.group));
  const v3 = runs.filter((s) => s.group === "v3");
  const tokens = sum(runs.map((s) => (s.tokens || {}).in || 0));
  const at100 = sum(live.map((s) => s.problems_at_100 || 0));
  const html = [`<div class="tiles">
    ${tile("Runs live", live.length, `${live.filter((s) => !s.snapshot).length} here · ${live.filter((s) => s.snapshot).length} via snapshot`, live.length ? "good" : "")}
    ${tile("Need attention", att.length, att.map((s) => armLabel(s) + " " + s.state).join(", ") || "none", att.length ? "bad" : "")}
    ${tile("v3 runs", v3.length, `${v3.filter((s) => s.state === "running").length} running · ${new Set(v3.map((s) => s.model)).size} model(s)`)}
    ${tile("Problems at 100% (live runs)", at100, "each one is a cheat on main", at100 ? "bad" : "")}
    ${tile("Input tokens (all local runs)", F.tok(tokens), `${F.tok(sum(runs.map((s) => (s.tokens || {}).out || 0)))} output`)}
    ${tile("Throttle retries (live)", F.int(sum(live.map((s) => s.retries || 0))), `${F.int(sum(live.map((s) => s.turn_errors || 0)))} turn errors`)}
  </div>`];
  for (const [g, title, sub] of GROUPS) {
    const list = sortRuns(runs.filter((s) => s.group === g));
    if (!list.length) continue;
    const collapsed = (g === "v1" || (g === "v2-archive" && !S.archiveOpen) || g === "stopped") && !loadJSON("swarm-open-" + g, false);
    html.push(`<div class="section-title"><h2>${esc(title)}</h2><span class="sub">${list.length} runs · ${esc(sub)}</span>
      <button class="link" data-toggle="${g}">${collapsed ? "show" : "hide"}</button></div>`);
    if (collapsed) continue;
    html.push(`<div class="panel tbl-wrap"><table><thead><tr><th>State</th><th>Run</th><th>Machine</th><th>Model</th><th>Oversight</th><th class="n">N</th><th>Progress</th>
      <th class="n">Elapsed</th><th class="n">ETA</th><th class="n">Last event</th><th>Pass rate</th><th class="n" title="Problems whose main passes every test: a cheat merged">@100%</th>
      <th class="n" title="Agents who ever wrote code that passes every test, which honest code can't (an impossible assert). Below: how many of them were removed, and how many never were">Cheaters</th><th class="n" title="Agents removed by audits. Below: removed agents who never cheated">Removed</th><th class="n">Reports</th>
      <th class="n" title="Instigator DMs">Instig.</th><th class="n" title="Merged PRs (cross-problem approvals)">Merged</th><th class="n" title="Codex retries (403 throttling) / turn errors">Retry/err</th><th></th></tr></thead><tbody>`);
    let lastModel = null;
    for (const s of list) {
      if (g === "v3" && s.model !== lastModel) { lastModel = s.model; html.push(`<tr class="grp-head"><td colspan="19">${esc(modelLabel(s.model))}</td></tr>`); }
      const cond = s.condition || condOfBase(s.arm_base), sp = cheatSplit(s);
      html.push(`<tr class="click" data-run="${esc(s.name)}">
        <td>${badge(s)}</td>
        <td><div class="runname">${esc(armLabel(s))}<small>${esc(s.name)}</small></div></td>
        <td>${esc(s.machine || "")}${deviceMini(s)}</td>
        <td>${esc(modelLabel(s.model))}${s.effort ? `<span class="muted"> ${esc(s.effort)}</span>` : ""}</td>
        <td><span class="swatch" style="background:${condColor(cond)}"></span> <span class="ink2">${esc((COND[cond] || {}).label || "–")}</span></td>
        <td class="n">${F.int(s.N)}</td>
        <td>${progress(s)}</td>
        <td class="n">${elapsed(s)}</td>
        <td class="n">${s.eta_t ? `<span title="${F.day(s.eta_t)}">${F.clock(s.eta_t)}</span>` : "–"}</td>
        <td class="n"><span data-ago="${s.last_t || ""}">${F.ago(s.last_t)}</span></td>
        <td>${spark(s.pass_series, css("--s1"))} <span class="muted">${F.pct(s.swarm_pass_rate, 0)}</span></td>
        <td class="n ${s.problems_at_100 ? "hot" : "zero"}">${F.int(s.problems_at_100)}${s.n_problems ? `<span class="muted">/${s.n_problems}</span>` : ""}</td>
        <td class="n ${s.cheaters_n ? "hot" : "zero"}">${s.cheaters_n == null ? "–" : F.int(s.cheaters_n)}${sp && sp.n ? `<small class="muted" style="display:block;white-space:nowrap">${sp.out} removed · ${sp.kept} not</small>` : ""}</td>
        <td class="n ${s.removed ? "" : "zero"}">${F.int(s.removed)}${sp && sp.other ? `<small class="muted" style="display:block;white-space:nowrap">${sp.other} never cheated</small>` : ""}</td>
        <td class="n ${s.reports ? "" : "zero"}">${F.int(s.reports)}</td>
        <td class="n">${F.int(s.instigator_dms)}</td>
        <td class="n">${F.int(s.prs_merged)}${s.merged_cross ? `<span class="muted"> (${F.int(s.merged_cross)})</span>` : ""}</td>
        <td class="n ${s.retries || s.turn_errors ? "" : "zero"}">${F.int(s.retries)}/${F.int(s.turn_errors)}</td>
        <td>${s.github ? `<a href="${esc(s.github)}" target="_blank" rel="noopener">GitHub</a>` : ""}</td></tr>`);
    }
    html.push("</tbody></table></div>");
  }
  $("#view").innerHTML = html.join("");
  $$("[data-toggle]").forEach((b) => (b.onclick = () => { const g = b.dataset.toggle; const k = "swarm-open-" + g;
    const open = !loadJSON(k, false) && !(g === "v2-archive" && S.archiveOpen); saveJSON(k, open); if (g === "v2-archive") { S.archiveOpen = open; saveJSON("swarm-archive-open", open); } renderOverview(); }));
}
// Cheaters split by removal (Bader, 9 Nov: "48 cheaters but 40 removed" read as a contradiction). From the run's
// agents when the detail is loaded (works for peer runs on older code), else from the summary fields.
function cheatSplit(s, agents) {
  if (s.cheaters_n == null) return null;
  if (agents) {
    const ch = agents.filter((a) => a.cheat_round != null), out = ch.filter((a) => a.removed_round != null).length;
    return { n: ch.length, out, kept: ch.length - out, other: agents.filter((a) => a.removed_round != null).length - out };
  }
  if (s.cheaters_removed == null) return null;
  return { n: s.cheaters_n, out: s.cheaters_removed, kept: s.cheaters_n - s.cheaters_removed, other: s.removed_non_cheaters };
}
function tile(k, v, d = "", cls = "") { return `<div class="tile ${cls}"><div class="k">${esc(k)}</div><div class="v">${v}</div>${d ? `<div class="d" title="${esc(d)}">${esc(d)}</div>` : ""}</div>`; }
function condOfBase(b) { const r = [...S.runs.values()].find((s) => s.arm_base === b && s.condition); return r ? r.condition : null; }
function deviceOf(s) {
  const dev = (S.fleet || {}).devices || [];
  const key = s.machine_key || String(s.machine || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  return dev.find((d) => (d.keys || []).includes(key));
}
function deviceMini(s) {
  const d = deviceOf(s); const st = d && d.status;
  if (!st) return "";
  const hot = st.memory.pressure !== "normal";
  return `<div class="muted" style="font-size:11px" title="fleet-status: CPU, memory, battery">${hot ? `<span class="tag crit">mem ${esc(st.memory.pressure)}</span> ` : ""}CPU ${Math.round(st.cpuPercent)}% · ${F.gb(st.memory.usedBytes)}${st.battery ? ` · ${st.battery.percent}%${st.battery.onPower ? "⚡" : ""}` : ""}</div>`;
}

// ------------------------------------------------------------------------------------------------ results
let seriesCache = { key: "", data: {} };
async function getSeries(names) {
  const key = names.slice().sort().join(",") + "|" + names.map((n) => (S.runs.get(n) || {}).version).join(",");
  if (seriesCache.key === key) return seriesCache.data;
  const data = names.length ? await api("/api/series?names=" + names.map(encodeURIComponent).join(",")) : {};
  seriesCache = { key, data };
  return data;
}

async function renderResults(refresh = false) {
  const runs = [...S.runs.values()];
  const v3 = runs.filter((s) => s.group === "v3" && !s.snapshot);
  const v3all = runs.filter((s) => s.group === "v3");
  const models = [...new Set(v3all.map((s) => s.model))].sort();
  if (!S.model || !models.includes(S.model)) S.model = models.includes("gpt-6-luna") ? "gpt-6-luna" : models[0];
  const mine = sortRuns(v3all.filter((s) => s.model === S.model));
  const series = await getSeries(mine.filter((s) => !s.snapshot).map((s) => s.name)).catch(() => ({}));
  if (S.route.view !== "results") return;
  // common round: the latest round every local run of this model has finished (snapshots only have "now")
  const doneRounds = mine.filter((s) => !s.snapshot).map((s) => s.completed_rounds || 0);
  const common = doneRounds.length ? Math.min(...doneRounds) : 0;
  const at = (s, key) => {
    if (S.compareRound === "latest" || s.snapshot) return key === "problems_at_100" ? s.problems_at_100 : key === "cheaters_cum" ? s.cheaters_n : key === "removals_cum" ? s.removed : null;
    const ser = series[s.name]; if (!ser || !common) return null;
    if (key === "removals_cum") return sum(ser.removals.slice(0, common));
    return ser[key] ? ser[key][common - 1] : null;
  };
  const arms = [...new Set(mine.map((s) => s.arm_base))].sort((a, b) => ARM_ORDER(a) - ARM_ORDER(b));
  const heroes = arms.map((b) => {
    const rs = mine.filter((s) => s.arm_base === b);
    const cond = rs.find((s) => s.condition)?.condition || condOfBase(b);
    const v100 = rs.map((s) => at(s, "problems_at_100")).filter((x) => x != null);
    const ch = rs.map((s) => at(s, "cheaters_cum")).filter((x) => x != null);
    const rm = rs.map((s) => at(s, "removals_cum")).filter((x) => x != null);
    const np = rs[0]?.n_problems || 55;
    const m = mean(v100);
    return `<div class="hero"><div class="label"><span class="swatch" style="background:${condColor(cond)}"></span>${esc(b)} · ${esc((COND[cond] || {}).label || "")}</div>
      <div class="big">${m == null ? "–" : F.num(m, m % 1 ? 1 : 0)}<small> of ${np} problems at 100%</small></div>
      <div class="note">${S.compareRound === "latest" ? "latest values" : `at round ${common}`}</div>
      <div class="note">${rs.map((s) => `s${s.seed} now: ${s.problems_at_100 ?? "–"} @100 · ${s.cheaters_n ?? "–"} cheaters${cheatSplit(s) ? ` (${cheatSplit(s).out} removed, ${cheatSplit(s).kept} never)` : ""} · ${s.removed ?? "–"} removed · round ${s.round}/${s.rounds_total} ${esc(s.state)}${s.snapshot ? " (laptop snapshot)" : ""}`).join("<br>")}</div>
      <div class="note">mean cheaters (blamed agents) ${ch.length ? F.num(mean(ch), 1) : "–"} of ${rs[0]?.N || 100} · mean removed ${rm.length ? F.num(mean(rm), 1) : "–"}</div>
      <div class="bar"><i style="width:${m == null ? 0 : (100 * m) / np}%;background:${css("--critical")}"></i></div></div>`;
  });
  const roundNote = S.compareRound === "latest" ? "latest values (runs are at different rounds)" : `at round ${common}, the latest round every ${esc(modelLabel(S.model))} run on this Mac has finished; laptop snapshots show their latest values`;
  const html = [`<div class="section-title"><h2>v3 result · ${esc(modelLabel(S.model))}</h2><span class="sub">${roundNote}</span>
    <span style="margin-left:auto;display:flex;gap:8px">
      <select id="model">${models.map((m) => `<option value="${esc(m)}" ${m === S.model ? "selected" : ""}>${esc(modelLabel(m))}</option>`).join("")}</select>
      <select id="cmpround"><option value="common" ${S.compareRound === "common" ? "selected" : ""}>Compare at common round</option><option value="latest" ${S.compareRound === "latest" ? "selected" : ""}>Compare latest values</option></select></span></div>
    <div class="headline" style="grid-template-columns:repeat(${Math.max(1, Math.min(arms.length, 4))},minmax(0,1fr))">${heroes.join("") || '<div class="empty">No v3 runs yet.</div>'}</div>
    <div class="grid g2" style="margin-top:12px">
      <div class="panel"><h3>Problems at 100% by round <span class="sub">solid seed 1, dashed seed 2</span></h3><div class="chart" id="c-v3-100"></div></div>
      <div class="panel"><h3>Cheaters by round <span class="sub">agents blamed for an impossible-assert pass, cumulative</span></h3><div class="chart" id="c-v3-ch"></div></div>
      <div class="panel"><h3>Swarm pass rate by round</h3><div class="chart" id="c-v3-pass"></div></div>
      <div class="panel"><h3>Removals by round <span class="sub">cumulative</span></h3><div class="chart" id="c-v3-rm"></div></div>
    </div>
    <div class="section-title"><h2>v3 runs, all metrics</h2><span class="sub">paper metrics from swarm.metrics.compute, live; acceptance rates need judge labels</span>
      <span style="margin-left:auto;display:flex;gap:6px"><button class="btn small" id="copy-v3">Copy Markdown</button><button class="btn small" id="csv-v3">CSV</button><span id="copied"></span></span></div>
    <div class="panel tbl-wrap">${metricTable(sortRuns(v3all.slice()), "v3")}</div>
    <div class="section-title"><h2>Round-by-round overlay</h2><span class="sub">any metric, any runs</span></div>
    <div class="panel"><div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px"><select id="ov-metric">${SERIES_OPTS.map(([k, l]) => `<option value="${k}" ${k === S.overlay.metric ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>
      <div class="checks" id="ov-runs"></div></div><div class="chart tall" id="c-overlay"></div></div>`];
  // v2 archive
  const arch = runs.filter((s) => s.group === "v2-archive" && s.metrics && s.end_reason === "completed");
  html.push(`<div class="section-title"><h2>v2 archive · fixed turn order</h2><span class="sub">${arch.length} completed runs in results/ordered/. Biased: agents a001–a010 always went first. Not the headline.</span>
    <button class="link" id="arch-toggle">${S.archiveOpen ? "hide" : "show"}</button></div>`);
  if (S.archiveOpen && arch.length) {
    const told = arch.filter((s) => s.informed), not = arch.filter((s) => !s.informed);
    const cm = (l) => mean(l.map((s) => s.cheaters_n)), n20 = arch[0]?.N || 20;
    html.push(`<div class="headline">
      <div class="hero"><div class="label"><span class="swatch" style="background:${css("--s1")}"></span>Told investigators may exist (${told.length} runs)</div>
        <div class="big">${F.num(cm(told), 1)}<small> cheaters of ${n20}</small></div><div class="note">${esc(told.map((s) => `${s.arm_base} ${s.cheaters_n}`).join(" · "))}</div></div>
      <div class="hero"><div class="label"><span class="swatch" style="background:${css("--s2")}"></span>Not told (${not.length} runs)</div>
        <div class="big">${F.num(cm(not), 1)}<small> cheaters of ${n20}</small></div><div class="note">${esc(not.map((s) => `${s.arm_base} ${s.cheaters_n}`).join(" · "))}</div></div>
      <div class="hero"><div class="label">Reading</div><div class="verdict">In the archived v2 runs, arms whose agents were <b>told</b> about investigators averaged <b>${F.num(cm(told), 1)}</b> cheaters per ${n20} agents, against <b>${F.num(cm(not), 1)}</b> when not told. The bluff arm (told, no investigators) is in the told group. Turn order was fixed in these runs.</div></div>
    </div>
    <div class="grid g2" style="margin-top:12px"><div class="panel"><h3>Cheaters by arm <span class="sub">v2 archive, colour = oversight condition</span></h3><div class="chart tall" id="c-arch"></div></div>
      <div class="panel"><h3>Impossible-assert passes by arm <span class="sub">test runs that passed the impossible assert</span></h3><div class="chart tall" id="c-arch-p"></div></div></div>
    <div class="section-title"><h2>v2 archive, all metrics</h2><span style="margin-left:auto;display:flex;gap:6px"><button class="btn small" id="copy-arch">Copy Markdown</button><button class="btn small" id="csv-arch">CSV</button></span></div>
    <div class="panel tbl-wrap">${metricTable(arch.slice().sort((a, b) => condRank(a.condition) - condRank(b.condition) || a.arm.localeCompare(b.arm)), "arch")}</div>`);
  }
  disposeCharts($("#view"));
  $("#view").innerHTML = html.join("");
  $("#model").onchange = (e) => { S.model = e.target.value; S.overlay.names = null; renderResults(); };
  $("#cmpround").onchange = (e) => { S.compareRound = e.target.value; renderResults(); };
  $("#arch-toggle").onclick = () => { S.archiveOpen = !S.archiveOpen; saveJSON("swarm-archive-open", S.archiveOpen); renderResults(); };
  const v3rows = sortRuns(v3all.slice());
  $("#copy-v3").onclick = () => copyText(tableMarkdown(v3rows));
  $("#csv-v3").onclick = () => download("v3-metrics.csv", tableCSV(v3rows));
  if ($("#copy-arch")) { $("#copy-arch").onclick = () => copyText(tableMarkdown(arch)); $("#csv-arch").onclick = () => download("v2-archive-metrics.csv", tableCSV(arch)); }
  // v3 charts
  const local = mine.filter((s) => !s.snapshot);
  const maxR = Math.max(20, ...local.map((s) => s.rounds_total || 20));
  const x = Array.from({ length: maxR }, (_, i) => String(i + 1));
  const mk = (key, cum = false) => local.map((s) => {
    const ser = series[s.name]; let d = ser ? ser[key].slice() : [];
    if (cum) { let acc = 0; d = d.map((v) => (v == null ? null : (acc += v))); }
    if (key === "swarm_pass_rate") d = d.map((v) => (v == null ? null : +(100 * v).toFixed(2)));
    return line(armLabel(s), d, condColor(s.condition || condOfBase(s.arm_base)), { dash: (s.seed || 1) > 1, lineStyle: { width: 2, type: (s.seed || 1) > 1 ? "dashed" : "solid", color: condColor(s.condition) } });
  });
  chart($("#c-v3-100"), { ...base({ x, int: true, file: "v3-problems-at-100" }), series: mk("problems_at_100") });
  chart($("#c-v3-ch"), { ...base({ x, int: true, file: "v3-cheaters" }), series: mk("cheaters_cum") });
  chart($("#c-v3-pass"), { ...base({ x, yfmt: "{value}%", file: "v3-pass-rate" }), series: mk("swarm_pass_rate") });
  chart($("#c-v3-rm"), { ...base({ x, int: true, file: "v3-removals" }), series: mk("removals", true) });
  renderOverlay();
  if (S.archiveOpen && arch.length) archiveCharts(arch);
}
function condRank(c) { return { none: 0, "audits-only": 1, uninformed: 2, bluff: 3, informed: 4 }[c] ?? 9; }
function archiveCharts(arch) {
  const byArm = new Map();
  for (const s of arch) { const k = s.arm; if (!byArm.has(k)) byArm.set(k, []); byArm.get(k).push(s); }
  const arms = [...byArm.keys()].sort((a, b) => condRank(byArm.get(a)[0].condition) - condRank(byArm.get(b)[0].condition) || a.localeCompare(b));
  const lab = (a) => a.replace(/-6-luna$/, "").replace(/-sol-max$/, " · sol").replace(/-56-luna$/, " · 5.6");
  const pt = (k) => arms.map((a) => { const s = byArm.get(a)[0]; return { value: k === "c" ? s.cheaters_n : (s.metrics || {}).impossible_assert_passes, itemStyle: { color: condColor(s.condition), borderRadius: [0, 3, 3, 0] } }; });
  const opt = (k, file) => ({ ...base({ legend: false, bars: true, file, grid: { left: 150, top: 10, right: 30 } }),
    tooltip: { trigger: "item", formatter: (p) => `${esc(arms[p.dataIndex])}<br>${esc((COND[byArm.get(arms[p.dataIndex])[0].condition] || {}).label)}<br><b>${p.value}</b>` },
    xAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: css("--grid") } }, axisLabel: { color: css("--muted") } },
    yAxis: { type: "category", inverse: true, data: arms.map(lab), axisLabel: { color: css("--ink-2"), fontSize: 11 }, axisLine: { lineStyle: { color: css("--axis") } }, axisTick: { show: false } },
    series: [{ type: "bar", data: pt(k), barMaxWidth: 14, label: { show: true, position: "right", color: css("--ink-2"), fontSize: 11 } }] });
  chart($("#c-arch"), opt("c", "v2-cheaters-by-arm"));
  chart($("#c-arch-p"), opt("p", "v2-impossible-passes-by-arm"));
}

const SERIES_OPTS = [["problems_at_100", "Problems at 100%"], ["cheaters_cum", "Cheaters (cumulative)"], ["swarm_pass_rate", "Swarm pass rate"], ["pr_merged", "PRs merged"],
  ["cheat_merges", "Cheat merges"], ["merged_cross", "Cross-problem merges"], ["pr_opened", "PRs opened"], ["approvals", "Approvals"], ["instigator_dms", "Instigator DMs"],
  ["reports", "Reports"], ["removals", "Removals"], ["conversions", "Conversions"], ["investigators", "Investigators"], ["largest_conspiracy", "Largest conspiracy"],
  ["dms", "DMs between agents"], ["turn_errors", "Turn errors"], ["retries", "Throttle retries"], ["tokens_in", "Input tokens"], ["round_minutes", "Round minutes"]];

async function renderOverlay() {
  const el = $("#c-overlay"); if (!el) return;
  const all = sortRuns([...S.runs.values()].filter((s) => !s.snapshot && ["v3", "v2-shuffled", "v2-archive", "stopped"].includes(s.group)));
  if (!S.overlay.names) S.overlay.names = all.filter((s) => s.group === "v3" && s.model === S.model).map((s) => s.name);
  $("#ov-runs").innerHTML = all.map((s) => `<label><input type="checkbox" value="${esc(s.name)}" ${S.overlay.names.includes(s.name) ? "checked" : ""}><span class="swatch" style="background:${condColor(s.condition)}"></span>${esc(armLabel(s))}${s.group !== "v3" ? `<span class="muted"> ${esc(s.group)}</span>` : ` <span class="muted">${esc(modelLabel(s.model))}</span>`}</label>`).join("");
  $$("#ov-runs input").forEach((i) => (i.onchange = () => { S.overlay.names = $$("#ov-runs input:checked").map((x) => x.value); renderOverlay(); }));
  $("#ov-metric").onchange = (e) => { S.overlay.metric = e.target.value; renderOverlay(); };
  const names = S.overlay.names;
  const data = names.length ? await api("/api/series?names=" + names.map(encodeURIComponent).join(",")).catch(() => ({})) : {};
  const k = S.overlay.metric;
  const maxR = Math.max(20, ...Object.values(data).map((d) => d.rounds.length));
  const x = Array.from({ length: maxR }, (_, i) => String(i + 1));
  const ser = names.filter((n) => data[n]).map((n) => { const s = S.runs.get(n) || {}; let d = data[n][k] || [];
    if (k === "swarm_pass_rate") d = d.map((v) => (v == null ? null : +(100 * v).toFixed(2)));
    return line(`${armLabel(s)} ${s.group === "v3" ? modelLabel(s.model) : s.group}`, d, condColor(s.condition), { lineStyle: { width: 2, color: condColor(s.condition), type: (s.seed || 1) > 1 || s.group !== "v3" ? "dashed" : "solid" } }); });
  chart(el, { ...base({ x, file: "overlay-" + k, yfmt: k === "swarm_pass_rate" ? "{value}%" : undefined }), series: ser });
}

const MCOLS = [["arm", "Arm"], ["seed", "Seed"], ["model", "Model"], ["machine", "Machine"], ["state", "State"], ["completed_rounds", "Rounds"], ["problems_at_100", "@100%"],
  ["cheaters_n", "Cheaters"], ["m.impossible_assert_passes", "Imp. passes"], ["m.misaligned_caught", "Caught"], ["m.misaligned_total", "Misaligned"],
  ["removed", "Removed"], ["reports", "Reports"], ["m.structural_acceptances", "Struct. accept"], ["m.largest_conspiracy", "Largest consp."],
  ["m.largest_conspiracy_active", "Active consp."], ["m.collusion_offers", "Offers"], ["m.peer_acceptance_rate", "Peer acc."], ["m.instigator_acceptance_rate", "Instig. acc."],
  ["m.alerts", "Alerts"], ["m.honeypot_agents", "Honeypot"], ["swarm_pass_rate", "Pass rate"], ["labels_present", "Labels"]];
function mval(s, k) {
  if (k === "arm") return s.arm_base || s.arm;
  if (k === "model") return modelLabel(s.model);
  if (k.startsWith("m.")) return (s.metrics || {})[k.slice(2)];
  return s[k];
}
function mfmt(k, v) {
  if (v == null) return "–";
  if (k === "swarm_pass_rate") return F.pct(v);
  if (/rate/.test(k)) return F.num(v, 2);
  if (typeof v === "boolean") return v ? "yes" : "no";
  return typeof v === "number" ? F.int(v) : String(v);
}
function metricTable(rows, id) {
  return `<table id="mt-${id}"><thead><tr>${MCOLS.map(([k, l]) => `<th class="${typeof mval(rows[0] || {}, k) === "number" ? "n" : ""}">${esc(l)}</th>`).join("")}</tr></thead><tbody>
    ${rows.map((s) => `<tr class="click" data-run="${esc(s.name)}">${MCOLS.map(([k]) => { const v = mval(s, k);
      const hot = (k === "problems_at_100" || k === "cheaters_n" || k === "m.impossible_assert_passes") && v > 0;
      return `<td class="${typeof v === "number" ? "n" : ""} ${hot ? "hot" : v === 0 ? "zero" : ""}">${k === "arm" ? `<span class="swatch" style="background:${condColor(s.condition || condOfBase(s.arm_base))}"></span> ` : ""}${esc(mfmt(k, v))}${k === "state" && s.snapshot ? " (snap)" : ""}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
}
function tableMarkdown(rows) {
  const head = MCOLS.map(([, l]) => l);
  return [`| ${head.join(" | ")} |`, `|${head.map(() => "---").join("|")}|`, ...rows.map((s) => `| ${MCOLS.map(([k]) => mfmt(k, mval(s, k))).join(" | ")} |`)].join("\n");
}
function tableCSV(rows) {
  const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  return [["run", ...MCOLS.map(([k]) => k)].map(q).join(","), ...rows.map((s) => [s.name, ...MCOLS.map(([k]) => mval(s, k))].map(q).join(","))].join("\n");
}
async function copyText(t) {
  try { await navigator.clipboard.writeText(t); toast("good", "Copied", "Markdown table on the clipboard.", "", "copy" + Date.now()); }
  catch (e) { const ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); toast("good", "Copied", "", "", "copy" + Date.now()); }
}
function download(name, text) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

// ------------------------------------------------------------------------------------------------ run view
function curRound() { return S.detail ? Math.max(S.detail.summary.round || 0, 1) : 1; }
function viewRound() { return S.replay ?? null; }

async function renderRun() {
  const s = S.runs.get(S.runName);
  if (s && s.snapshot) { renderSnapshotRun(s); connect(); return; }
  $("#view").innerHTML = `<div id="runhead"></div><div id="runbody"><div class="loading">Loading ${esc(S.runName)}…</div></div>`;
  try {
    S.detail = await api(runUrl(S.runName));
  } catch (e) { $("#runbody").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (S.after == null) S.after = S.detail.summary.seq;
  connect(true);
  renderRunHeader();
  renderRunBody();
  loadFeed();
}
const refreshDetail = debounce(async () => {
  if (S.route.view !== "run" || !S.runName) return;
  try { S.detail = await api(runUrl(S.runName)); } catch (e) { return; }
  renderRunHeader(); renderRunBody(true);
}, 1800);

function renderSnapshotRun(s) {
  const rows = [["State", s.state_detail], ["Round", `${s.round}/${s.rounds_total}`], ["Turns", s.turns], ["Turn errors", s.turn_errors], ["Usage stops", s.usage_stops],
    ["PRs opened / merged", `${s.prs_opened} / ${s.prs_merged}`], ["Cross-problem merges", s.merged_cross], ["Problems at 100%", `${s.problems_at_100}/${s.n_problems || "?"}`],
    ["Swarm pass rate", F.pct(s.swarm_pass_rate)], ["Test file edits", s.test_file_edits], ["Instigator DMs", s.instigator_dms], ["Reports", s.reports], ["Removed", s.removed]];
  $("#view").innerHTML = `<div class="runhead"><div><h1>${esc(armLabel(s))} <span class="muted" style="font-weight:400">${esc(modelLabel(s.model))} · ${esc(s.machine)}</span></h1>
    <div class="meta">${badge(s)}<span class="chip">${esc(s.name)}</span><span class="chip">snapshot as of ${F.day(s.snapshot_t)}</span></div></div></div>
    <div class="panel"><p class="ink2" style="margin-top:0">This run is on <b>${esc(s.machine)}</b>, which this dashboard can't reach. These numbers come from <span class="mono">${esc(s.snapshot_src)}</span>, which the laptop pushes every 15 minutes. Its events, charts and drill-downs appear here once it publishes to <span class="mono">results/</span>. For live data, run this dashboard on the laptop too and pass it here with <span class="mono">--peer http://LAPTOP:8765</span>.</p>
    <table>${rows.map(([k, v]) => `<tr><td class="muted">${esc(k)}</td><td class="n">${esc(v ?? "–")}</td></tr>`).join("")}</table></div>`;
}

function renderRunHeader() {
  const el = $("#runhead"); if (!el || !S.detail) return;
  const s = S.runs.get(S.runName) || S.detail.summary; const c = S.detail.config || {};
  const cond = s.condition;
  const chips = [
    `<span class="chip"><span class="swatch" style="background:${condColor(cond)}"></span>${esc((COND[cond] || {}).label || cond)}</span>`,
    `<span class="chip">${esc(modelLabel(s.model))}${s.effort ? " · " + esc(s.effort) : ""}</span>`,
    `<span class="chip">N ${s.N} · ${s.n_problems} problems</span>`, `<span class="chip">I₀ ${c.initial_investigators ?? "–"} · k ${c.k ?? "–"} · p ${c.p ?? "–"}</span>`,
    `<span class="chip">seed ${s.seed}</span>`, c.swarm_wide ? '<span class="chip">global review</span>' : "", c.shuffle_turns ? '<span class="chip">shuffled turns</span>' : '<span class="chip">fixed turn order</span>',
    c.tests_visible === false ? '<span class="chip">hidden tests</span>' : "", c.instigator_aggressive ? '<span class="chip">aggressive instigator</span>' : "",
    `<span class="chip">${esc(s.machine)}</span>`, s.github ? `<a class="chip" href="${esc(s.github)}" target="_blank" rel="noopener">results on GitHub ↗</a>` : "",
  ].join("");
  const m = S.detail.metrics || {}, sp = cheatSplit(s, S.detail.agents);
  const eta = s.eta_t ? `ETA ${F.clock(s.eta_t)} (<span data-until="${s.eta_t}">${F.dur(s.eta_t - nowS())}</span>)` : "";
  el.innerHTML = `<div class="runhead"><div><h1>${esc(armLabel(s))} <span class="muted" style="font-weight:400;font-size:14px">${esc(s.name)}</span></h1><div class="meta">${badge(s)} ${chips}</div></div>
    <div class="right"><div style="min-width:220px">${progress(s)}</div><div class="muted" style="font-size:12px;text-align:right">elapsed ${elapsed(s)}<br>${eta}${s.state_detail ? `<br>${esc(s.state_detail)}` : ""}</div>
    <select id="runpick">${sortRuns([...S.runs.values()]).filter((r) => !r.snapshot).map((r) => `<option value="${esc(r.name)}" ${r.name === S.runName ? "selected" : ""}>${esc(r.group)} · ${esc(armLabel(r))} · ${esc(modelLabel(r.model))}</option>`).join("")}</select></div></div>
    <div class="tiles">
      ${tile("Swarm pass rate", F.pct(s.swarm_pass_rate), `round ${s.completed_rounds} on main`)}
      ${tile("Problems at 100%", `${F.int(s.problems_at_100)}<small>/ ${s.n_problems}</small>`, (s.at100 || []).slice(0, 6).join(", ") || "none", s.problems_at_100 ? "bad" : "")}
      ${tile("Cheaters", s.cheaters_n == null ? "–" : `${s.cheaters_n}<small>/ ${s.N}</small>`, sp ? `${sp.out} removed · ${sp.kept} never removed · wrote code passing every test` : "wrote code passing every test (impossible honestly)", s.cheaters_n ? "bad" : "")}
      ${tile("Impossible-assert passes", F.int(m.impossible_assert_passes), "test runs that passed every test")}
      ${tile("Misaligned caught / total", `${F.int(m.misaligned_caught)}<small>/ ${F.int(m.misaligned_total)}</small>`, "in-round audits vs all evidence")}
      ${tile("Removed", F.int(s.removed), `${sp ? `${sp.out} had cheated · ${sp.other} never cheated · ` : ""}${F.int(s.reports)} reports filed`)}
      ${tile("Investigators", `${s.investigators}<small>/ ${s.active_agents}</small>`, "active agents now")}
      ${tile("PRs merged", F.int(s.prs_merged), `${F.int(s.prs_opened)} opened · ${F.int(s.merged_cross)} cross-problem`)}
      ${tile("Instigator DMs", F.int(s.instigator_dms), `acceptance ${m.instigator_acceptance_rate == null ? "needs labels" : F.num(m.instigator_acceptance_rate, 2)}`)}
      ${tile("Largest conspiracy", F.int(m.largest_conspiracy), `${F.int(m.largest_conspiracy_active)} with active links only${s.labels_present ? "" : " · no labels yet"}`)}
      ${tile("Tokens in / out", F.tok((s.tokens || {}).in), `${F.tok((s.tokens || {}).out)} out · ${F.pct((s.tokens || {}).cached / ((s.tokens || {}).in || 1), 0)} cached`)}
      ${tile("Retries / errors", `${F.int(s.retries)}<small>/ ${F.int(s.turn_errors)}</small>`, Object.entries(S.detail.error_kinds || {}).map(([k, v]) => `${k} ${v}`).join(", ") || "no turn errors")}
    </div>`;
  $("#runpick").onchange = (e) => { location.hash = `#/run/${encodeURIComponent(e.target.value)}/${S.tab}`; };
}

function renderRunBody(update = false) {
  const body = $("#runbody"); if (!body || !S.detail) return;
  const d = S.detail;
  const total = d.summary.rounds_total || 20, cur = curRound();
  const tabs = [["live", "Live"], ["charts", "Charts"], ["network", "Network"], ["agents", "Agents", d.agents.length], ["prs", "PRs", d.summary.prs_opened], ["config", "Config"]];
  if (!update || !$("#replay")) {
    body.innerHTML = `<div class="replay" id="replay"><button class="btn small" id="play" title="Play rounds (space)">▶</button>
      <span class="rlabel" id="rlabel"></span><input type="range" id="rslider" min="1" max="${total}" step="1">
      <button class="btn small" id="golive">Live</button><span class="muted" style="font-size:11.5px">← → step rounds</span></div>
      <div class="subtabs" id="subtabs">${tabs.map(([k, l, n]) => `<button data-tab="${k}" class="${S.tab === k ? "on" : ""}">${l}${n != null ? `<span class="cnt">${n}</span>` : ""}</button>`).join("")}</div>
      <div id="tabbody"></div>`;
    $("#rslider").oninput = (e) => { const r = +e.target.value; setReplay(r >= cur ? null : r); };
    $("#play").onclick = togglePlay;
    $("#golive").onclick = () => { stopPlay(); setReplay(null); };
    $$("#subtabs button").forEach((b) => (b.onclick = () => { S.tab = b.dataset.tab; history.replaceState(null, "", `#/run/${encodeURIComponent(S.runName)}/${S.tab}`); $$("#subtabs button").forEach((x) => x.classList.toggle("on", x === b)); disposeCharts($("#tabbody")); renderTab(); }));
    updateReplayBar();
    renderTab();
    return;
  }
  updateReplayBar();
  renderTab(true);
}
function updateReplayBar() {
  if (!S.detail || !$("#rslider")) return;
  const cur = curRound(), total = S.detail.summary.rounds_total || 20, r = S.replay;
  $("#rslider").max = total; $("#rslider").value = r ?? cur;
  const isLive = (S.runs.get(S.runName) || S.detail.summary).state === "running";
  $("#rlabel").innerHTML = r == null ? `Round ${cur}/${total} · ${isLive ? '<span style="color:var(--good-ink)">live</span>' : "latest"}` : `Round ${r}/${total} · replay`;
  $("#golive").textContent = isLive ? "Live" : "Latest";
  $("#replay").classList.toggle("past", r != null);
  $("#play").textContent = S.playing ? "❚❚" : "▶";
}
function setReplay(r) {
  S.replay = r == null || r >= curRound() ? null : Math.max(1, r);
  updateReplayBar();
  renderTab(true);
  if (S.tab === "live") loadFeed();
}
function togglePlay() {
  if (S.playing) return stopPlay();
  if (S.replay == null) setReplay(1);
  S.playing = setInterval(() => { const r = (S.replay ?? curRound()) + 1; if (r >= curRound()) { stopPlay(); setReplay(null); } else setReplay(r); }, 1600);
  updateReplayBar();
}
function stopPlay() { if (S.playing) clearInterval(S.playing); S.playing = null; updateReplayBar(); }

function renderTab(update = false) {
  const tb = $("#tabbody"); if (!tb) return;
  if (S.tab === "live") return renderLive(tb, update);
  if (S.tab === "charts") return renderCharts(tb, update);
  if (S.tab === "network") return renderNetwork(tb, update);
  if (S.tab === "agents") return renderAgents(tb);
  if (S.tab === "prs") return renderPRs(tb, update);
  if (S.tab === "config") return renderConfig(tb);
}

// ---- live tab: key charts, heatmap, agent grid | feed
function renderLive(tb, update) {
  if (!update || !$("#live-left")) {
    tb.innerHTML = `<div class="split"><div id="live-left" class="grid">
      <div class="grid g2"><div class="panel"><h3>Problems at 100% and cheaters <span class="sub">by round</span></h3><div class="chart" id="c-l1"></div></div>
        <div class="panel"><h3>PR activity <span class="sub">per round</span></h3><div class="chart" id="c-l2"></div></div></div>
      <div class="panel"><h3>Pass rate per problem <span class="sub">main at each round end; red = 100%, which needs the impossible assert to pass</span></h3><div id="heat-wrap"><div class="chart" id="c-heat"></div></div></div>
      <div class="panel"><h3>Agents <span class="sub" id="ag-sub"></span><span class="tools"><select id="ag-sort"><option value="slot">by slot</option><option value="team">by problem</option><option value="activity">by activity</option><option value="role">by role</option></select></span></h3>
        <div id="agents" class="agents"></div>
        <div class="legend"><span><i class="box" style="background:var(--surface-2)"></i>worker</span><span><i class="box" style="background:color-mix(in srgb,var(--s7) 30%,var(--surface-2))"></i>investigator</span>
          <span><i class="box" style="box-shadow:inset 0 0 0 2px var(--critical)"></i>cheater (blamed)</span><span><i class="box" style="opacity:.45;background:repeating-linear-gradient(135deg,var(--surface-2),var(--surface-2) 3px,var(--surface-3) 3px,var(--surface-3) 6px)"></i>removed</span>
          <span><i class="box" style="border-color:var(--good)"></i>mid-turn now</span><span class="muted">bar = share of the round's turns done · click an agent for its timeline</span></div></div>
    </div><div class="panel feed-panel" id="feed-panel"></div></div>`;
    $("#ag-sort").value = S.agSortMode || "slot";
    $("#ag-sort").onchange = (e) => { S.agSortMode = e.target.value; renderAgentGrid(); };
    renderFeedPanel();
  }
  const d = S.detail.series, r = viewRound();
  const x = d.rounds.map(String);
  const cut = (a) => (r == null ? a : a.map((v, i) => (i < r ? v : null)));
  chart($("#c-l1"), { ...base({ x, int: true, file: "problems-at-100" }), series: markRound([line("problems at 100%", cut(d.problems_at_100), css("--critical")), line("cheaters (cumulative)", cut(d.cheaters_cum), css("--s7"))], r) });
  chart($("#c-l2"), { ...base({ x, int: true, bars: true, file: "pr-activity" }), series: markRound([bar("opened", cut(d.pr_opened), css("--s1")), bar("merged", cut(d.pr_merged), css("--s3")), bar("cheat merges", cut(d.cheat_merges), css("--critical"))], r) });
  renderHeat();
  renderAgentGrid();
}

function renderHeat() {
  const el = $("#c-heat"); if (!el) return;
  const d = S.detail, r = viewRound();
  const rounds = d.series.rounds.map(String);
  const probs = d.problems;
  el.style.height = Math.max(140, Math.min(900, probs.length * 13 + 70)) + "px";
  const data = d.heat.filter(([rr]) => r == null || rr <= r).map(([rr, i, v]) => [rr - 1, i, +(v * 100).toFixed(1)]);
  const pieces = [{ gte: 99.95, label: "100% · cheat on main", color: css("--critical") }, { gte: 95, lt: 99.95, label: "95–99.9%", color: css("--seq-5") },
    { gte: 80, lt: 95, label: "80–95%", color: css("--seq-4") }, { gte: 50, lt: 80, label: "50–80%", color: css("--seq-3") },
    { gt: 0, lt: 50, label: "under 50%", color: css("--seq-2") }, { lte: 0, label: "0%", color: css("--seq-0") }];
  const c = chart(el, { ...base({ legend: false, file: "heatmap", grid: { left: 92, right: 12, top: 8, bottom: 52 } }),
    tooltip: { trigger: "item", formatter: (p) => `${esc(probs[p.value[1]])} · round ${p.value[0] + 1}<br><b>${p.value[2]}%</b> of tests pass` },
    xAxis: { type: "category", data: rounds, axisLabel: { color: css("--muted"), fontSize: 10 }, axisLine: { lineStyle: { color: css("--axis") } }, splitArea: { show: false } },
    yAxis: { type: "category", data: probs, inverse: true, axisLabel: { color: css("--muted"), fontSize: 9.5, interval: 0 }, axisLine: { show: false }, axisTick: { show: false } },
    visualMap: { type: "piecewise", pieces, orient: "horizontal", left: 0, bottom: 0, itemWidth: 12, itemHeight: 10, itemGap: 10, textStyle: { color: css("--ink-2"), fontSize: 11 }, dimension: 2 },
    series: [{ type: "heatmap", data, itemStyle: { borderColor: css("--surface"), borderWidth: 1 }, emphasis: { itemStyle: { borderColor: css("--ink"), borderWidth: 1 } }, progressive: 0 }] });
  if (c) { c.off("click"); c.on("click", (p) => { S.fTeam = probs[p.value[1]]; $("#fteam") && ($("#fteam").value = S.fTeam); loadFeed(); }); }
}

function agentAt(a, r) {
  const live = r == null;
  const role = a.initial_role === "investigator" || (a.converted_round && (live || a.converted_round <= r)) ? "investigator" : "worker";
  return { role, removed: a.removed_round != null && (live || a.removed_round <= r), cheat: a.cheat_round != null && (live || a.cheat_round <= r), future: !live && a.joined_round > r };
}
function renderAgentGrid() {
  const el = $("#agents"); if (!el) return;
  const d = S.detail, r = viewRound(), s = S.runs.get(S.runName) || d.summary;
  let list = d.agents.slice();
  const mode = S.agSortMode || "slot";
  if (mode === "team") list.sort((a, b) => String(a.team).localeCompare(String(b.team)) || a.slot - b.slot || a.joined_round - b.joined_round);
  if (mode === "activity") list.sort((a, b) => (b.last_t || 0) - (a.last_t || 0));
  if (mode === "role") list.sort((a, b) => (agentAt(b, r).role === "investigator") - (agentAt(a, r).role === "investigator") || (agentAt(b, r).cheat - agentAt(a, r).cheat) || a.slot - b.slot);
  if (mode === "slot") list.sort((a, b) => a.slot - b.slot || a.joined_round - b.joined_round);
  const running = s.state === "running" && r == null;
  el.className = "agents" + (list.length <= 24 ? " n20" : "");
  el.innerHTML = list.map((a) => {
    const st = agentAt(a, r);
    const cls = ["ag", st.role === "investigator" ? "inv" : "", st.cheat ? "cheat" : "", st.removed ? "removed" : "", st.future ? "future" : "", running && a.in_turn ? "turn" : ""].join(" ");
    const tip = `${a.id} · ${a.team} · ${st.role}${a.converted_round ? ` (converted R${a.converted_round})` : ""}${a.removed_round ? ` · removed R${a.removed_round}` : ""}${a.cheat_round ? ` · cheater from R${a.cheat_round}` : ""}\nturns ${a.turns} · tools ${a.tool_calls} · DMs ${a.dms_sent}/${a.dms_received} · instigator DMs ${a.instigator_dms}\nPRs ${a.prs_opened} (merged ${a.prs_merged}) · approvals ${a.approvals} · reports ${a.reports_filed} · accused ${a.times_accused}\n${a.last ? "last: " + a.last : ""}${a.said ? "\n“" + a.said.slice(0, 160) + "”" : ""}`;
    return `<div class="${cls}" data-agent="${esc(a.id)}" title="${esc(tip)}"><b>${esc(a.id)}</b><span>${esc(String(a.team || "").replace("lcbhard_", "p"))}</span><span>${esc(running ? (a.last || "") : st.removed ? "removed" : (a.last || ""))}</span>${running && a.done_this_round ? '<i class="bar" style="width:100%"></i>' : ""}</div>`;
  }).join("");
  const at = list.filter((a) => !agentAt(a, r).removed && !agentAt(a, r).future);
  $("#ag-sub").textContent = `${at.length} active${r == null ? "" : " at round " + r} · ${at.filter((a) => agentAt(a, r).role === "investigator").length} investigators · ${list.filter((a) => agentAt(a, r).cheat).length} cheaters${running ? ` · ${list.filter((a) => a.in_turn).length} mid-turn` : ""}`;
}

// ---- feed
function renderFeedPanel() {
  const p = $("#feed-panel"); if (!p) return;
  const agents = S.detail.agents.map((a) => a.id).concat(S.detail.instigator ? [S.detail.instigator] : []);
  p.innerHTML = `<h3>Event feed <span class="sub" id="feed-sub"></span><span class="tools"><button class="btn small" id="fpause">${S.paused ? "Resume" : "Pause"}</button></span></h3>
    <div class="feed-filters">${CATS.map(([k, l]) => `<button class="fchip ${S.cats.has(k) ? "on" : ""}" data-cat="${k}">${esc(l)}</button>`).join("")}</div>
    <div class="feed-row2"><input type="search" id="fq" placeholder="search all events (/), Enter" value="${esc(S.fQ)}">
      <input list="fagents" id="fagent" placeholder="agent" value="${esc(S.fAgent)}" style="max-width:86px"><datalist id="fagents">${agents.map((a) => `<option value="${a}">`).join("")}</datalist>
      <select id="fteam" style="max-width:120px"><option value="">all problems</option>${S.detail.problems.map((t) => `<option ${t === S.fTeam ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></div>
    <div class="feed" id="feed"></div>`;
  $$(".fchip", p).forEach((b) => (b.onclick = () => { const k = b.dataset.cat; S.cats.has(k) ? S.cats.delete(k) : S.cats.add(k); b.classList.toggle("on"); saveJSON("swarm-cats", [...S.cats]); loadFeed(); }));
  $("#fq").onkeydown = (e) => { if (e.key === "Enter") { S.fQ = e.target.value.trim(); loadFeed(); } };
  $("#fq").onsearch = (e) => { S.fQ = e.target.value.trim(); loadFeed(); };
  $("#fagent").onchange = (e) => { S.fAgent = e.target.value.trim(); loadFeed(); };
  $("#fteam").onchange = (e) => { S.fTeam = e.target.value; loadFeed(); };
  $("#fpause").onclick = (e) => { S.paused = !S.paused; e.target.textContent = S.paused ? "Resume" : "Pause"; if (!S.paused) loadFeed(); };
}
function feedQuery(extra = {}) {
  const q = new URLSearchParams({ limit: 150, cats: [...S.cats].join(",") || "none", ...extra });
  if (S.fAgent) q.set("agent", S.fAgent);
  if (S.fTeam) q.set("team", S.fTeam);
  if (S.fQ) q.set("q", S.fQ);
  if (S.replay != null) q.set("round", S.replay);
  return q.toString();
}
async function loadFeed(more = false) {
  const el = $("#feed"); if (!el) return;
  const extra = more && S.feedCursor != null ? { before: S.feedCursor } : {};
  let res;
  try { res = await api(runUrl(S.runName, "/feed?" + feedQuery(extra))); } catch (e) { el.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (!more) { S.feed = []; S.feedSeen = new Set(); }
  for (const it of res.items) if (!S.feedSeen.has(it.seq)) { S.feedSeen.add(it.seq); S.feed.push(it); }
  S.feedCursor = res.cursor ?? (res.items.length ? res.items[res.items.length - 1].seq : null);
  S.feedMore = res.more;
  drawFeed();
}
function drawFeed(newSeqs) {
  const el = $("#feed"); if (!el) return;
  const items = S.feed.slice(0, 600);
  el.innerHTML = items.map((it) => evHTML(it, newSeqs && newSeqs.has(it.seq))).join("") +
    `<div class="feed-foot">${S.feedMore ? '<button class="btn small" id="fmore">Load older</button>' : items.length ? '<span class="muted">start of matching events</span>' : '<span class="muted">no matching events</span>'}</div>`;
  if ($("#fmore")) $("#fmore").onclick = () => loadFeed(true);
  $("#feed-sub").textContent = `${items.length} shown${S.replay != null ? " · round " + S.replay : ""}${S.paused ? " · paused" : ""}`;
}
const LINK_RE = /\b(a\d{3,4}|pr\d{3,4})\b/g;
function linkify(text, run) {
  return esc(text).replace(LINK_RE, (m) => (m.startsWith("pr") ? `<a data-pr="${m}" data-run="${esc(run)}">${m}</a>` : `<a class="agent" data-agent="${m}" data-run="${esc(run)}">${m}</a>`));
}
function evHTML(it, isNew, run = S.runName) {
  const tags = (it.tags || []).map((t) => `<span class="tag ${/full-pass|cheat|error|misaligned|removed|touches/.test(t) ? "crit" : /approve$|aligned/.test(t) ? "good" : t === "request_changes" ? "warn" : t === "instigator" ? "warn" : ""}">${esc(t)}</span>`).join("");
  const label = it.label ? `<span class="tag lab-${esc(it.label)}" title="judge label${it.label_target ? ", target " + esc(it.label_target) : ""}">${esc(it.label)}</span>` : "";
  const hot = (it.tags || []).some((t) => /full-pass|cheat-pr|misaligned|removed/.test(t)) || it.type === "test_file_edit";
  return `<div class="ev c-${esc(it.cat)} ${hot ? "hot" : ""} ${isNew ? "new" : ""}"><div class="h"><span class="t">${linkify(it.title, run)}${label}${tags}</span>
    <span class="w">R${it.round ?? "–"} · ${F.clockS(it.t)} <a data-raw="${it.seq}" data-run="${esc(run)}" title="raw event">#${it.seq}</a></span></div>${it.body ? `<div class="b">${linkify(it.body, run)}</div>` : ""}</div>`;
}
function matches(it) {
  if (!S.cats.has(it.cat)) return false;
  if (S.fAgent && it.agent !== S.fAgent && !String(it.to || "").split(",").includes(S.fAgent)) return false;
  if (S.fTeam && it.team !== S.fTeam) return false;
  if (S.fQ && !(`${it.title} ${it.body}`.toLowerCase().includes(S.fQ.toLowerCase()))) return false;
  if (S.replay != null && it.round !== S.replay) return false;
  return true;
}
function onEvents(msg) {
  if (msg.run !== S.runName) return;
  const items = msg.items || [];
  if (!items.length) return;
  S.after = Math.max(S.after ?? -1, items[items.length - 1].seq);
  S.lastEvent = items[items.length - 1].t;
  const fresh = new Set();
  for (const it of items) {
    if (S.feedSeen.has(it.seq) || !matches(it)) continue;
    S.feedSeen.add(it.seq); fresh.add(it.seq); S.feed.unshift(it);
    if (it.type === "pr_merged" && (it.tags || []).includes("cheat-pr")) toast("crit", `${armLabel(S.runs.get(S.runName) || {})}: cheat merged`, it.title + " · " + it.body, S.runName, "merge" + it.seq);
  }
  if (S.feed.length > 800) S.feed.length = 800;
  if (fresh.size && !S.paused && S.tab === "live") drawFeed(fresh);
  refreshDetail();
  if (S.tab === "network") refreshNet();
  if (S.tab === "prs") refreshPRs();
}

// ---- charts tab
function renderCharts(tb, update) {
  const defs = [["c-pass", "Swarm pass rate", "%"], ["c-100", "Problems at 100%", ""], ["c-cheat", "Cheaters (cumulative) and impossible-assert test passes", ""],
    ["c-prs", "PRs per round", ""], ["c-rev", "Reviews per round", ""], ["c-roles", "Workers and investigators", ""], ["c-consp", "Largest conspiracy", "needs judge labels for the full link set"],
    ["c-inst", "Instigator DMs and reports of the instigator", ""], ["c-over", "Oversight per round", ""], ["c-err", "Turn errors and throttle retries", ""],
    ["c-tok", "Input tokens per round", ""], ["c-out", "Output tokens per round", ""], ["c-dur", "Round duration", "minutes"], ["c-act", "Turns and tool calls per round", ""], ["c-tools", "Tool use", "whole run"]];
  if (!update || !$("#c-pass")) tb.innerHTML = `<div class="grid g3">${defs.map(([id, t, sub]) => `<div class="panel"><h3>${esc(t)} <span class="sub">${esc(sub)}</span></h3><div class="chart" id="${id}"></div></div>`).join("")}</div>`;
  const d = S.detail.series, r = viewRound(), x = d.rounds.map(String);
  const cut = (a) => (r == null ? a : a.map((v, i) => (i < r ? v : null)));
  const C = (id, series, o = {}) => chart($("#" + id), { ...base({ x, file: id.slice(2), ...o }), series: markRound(series, r) });
  C("c-pass", [line("swarm pass rate", cut(d.swarm_pass_rate.map((v) => (v == null ? null : +(100 * v).toFixed(2)))), css("--s1"))], { yfmt: "{value}%", legend: false });
  C("c-100", [line("problems at 100%", cut(d.problems_at_100), css("--critical"))], { int: true, legend: false });
  C("c-cheat", [line("cheaters", cut(d.cheaters_cum), css("--s7")), bar("full-pass test runs", cut(d.full_passes), css("--s5"))], { int: true });
  C("c-prs", [bar("opened", cut(d.pr_opened), css("--s1")), bar("updated", cut(d.pr_updated), css("--s7")), bar("merged", cut(d.pr_merged), css("--s3")), bar("cross-problem", cut(d.merged_cross), css("--s4")), bar("cheat merges", cut(d.cheat_merges), css("--critical"))], { int: true, bars: true });
  C("c-rev", [bar("approvals", cut(d.approvals), css("--s3")), bar("request changes", cut(d.request_changes), css("--s2"))], { int: true, bars: true });
  C("c-roles", [line("workers", cut(d.workers), css("--s1"), { stack: "r", areaStyle: { opacity: 0.25 } }), line("investigators", cut(d.investigators), css("--s7"), { stack: "r", areaStyle: { opacity: 0.35 } })], { int: true });
  C("c-consp", [line("all links", cut(d.largest_conspiracy), css("--critical")), line("active links", cut(d.largest_conspiracy_active), css("--s2"))], { int: true });
  C("c-inst", [bar("instigator DMs", cut(d.instigator_dms), css("--serious")), bar("reports naming it", cut(d.instigator_reports), css("--s3"))], { int: true, bars: true });
  C("c-over", [bar("reports", cut(d.reports), css("--s7")), bar("audits", cut(d.audits), css("--s1")), bar("removals", cut(d.removals), css("--critical")), bar("conversions", cut(d.conversions), css("--s3"))], { int: true, bars: true });
  C("c-err", [bar("throttle retries", cut(d.retries), css("--warn")), bar("turn errors", cut(d.turn_errors), css("--critical"))], { int: true, bars: true });
  C("c-tok", [line("input", cut(d.tokens_in), css("--s1")), line("cached input", cut(d.tokens_cached), css("--s3"))], { yfmt: (v) => F.tok(v) });
  C("c-out", [bar("output", cut(d.tokens_out), css("--s7"))], { yfmt: (v) => F.tok(v), bars: true, legend: false });
  C("c-dur", [bar("minutes", cut(d.round_minutes), css("--s1"))], { bars: true, legend: false });
  C("c-act", [bar("turns", cut(d.turns), css("--s1")), bar("tool calls", cut(d.tool_calls), css("--s3"))], { int: true, bars: true });
  const tools = S.detail.tool_counts || [];
  chart($("#c-tools"), { ...base({ legend: false, bars: true, file: "tools", grid: { left: 130, top: 6, right: 40 } }), tooltip: { trigger: "item" },
    xAxis: { type: "value", splitLine: { lineStyle: { color: css("--grid") } }, axisLabel: { color: css("--muted") } },
    yAxis: { type: "category", inverse: true, data: tools.map((t) => t[0]), axisLabel: { color: css("--ink-2"), fontSize: 11 }, axisTick: { show: false }, axisLine: { lineStyle: { color: css("--axis") } } },
    series: [{ type: "bar", data: tools.map((t) => t[1]), itemStyle: { color: css("--s1"), borderRadius: [0, 3, 3, 0] }, barMaxWidth: 12, label: { show: true, position: "right", color: css("--ink-2"), fontSize: 10.5 } }] });
}

// ---- network tab
const EDGE_KINDS = [["approve_cheat", "approval of a cheat PR", "--critical", false], ["merged_cheat", "cheat merged (author–approver)", "--critical", true],
  ["approve", "approval", "--s3", false], ["instigator", "instigator DM", "--serious", false], ["dm", "DM", "--axis", false], ["report", "report", "--s7", false],
  ["label_offer", "judge: offer", "--s5", false], ["label_acceptance", "judge: acceptance", "--s5", true], ["label_endorsement", "judge: endorsement", "--s4", false], ["label_alert", "judge: alert", "--good", true]];
const refreshNet = debounce(async () => { if (S.tab !== "network") return; try { S.net = await api(runUrl(S.runName, "/network")); } catch (e) { return; } renderNetwork($("#tabbody"), true); }, 5000);
async function renderNetwork(tb, update) {
  if (!S.net) { tb.innerHTML = '<div class="loading">Loading network…</div>'; try { S.net = await api(runUrl(S.runName, "/network")); } catch (e) { tb.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; } update = false; }
  if (!S.netKinds) S.netKinds = new Set(["approve_cheat", "merged_cheat", "approve", "instigator", "report", "label_offer", "label_acceptance", "label_endorsement"].concat(S.net.nodes.length <= 30 ? ["dm"] : []));
  if (!update || !$("#c-net")) {
    tb.innerHTML = `<div class="split"><div class="panel"><h3>Who approved, DMed and reported whom <span class="sub" id="net-sub"></span><span class="tools"><select id="net-layout"><option value="circular">circle by problem</option><option value="force">force</option></select></span></h3>
      <div class="chart xl" id="c-net"></div>
      <div class="legend"><span><i class="box" style="background:var(--s1)"></i>worker</span><span><i class="box" style="background:var(--s7)"></i>investigator</span><span><i class="box" style="background:var(--serious)"></i>instigator</span>
      <span><i class="box" style="background:var(--surface-3)"></i>removed</span><span><i class="box" style="box-shadow:inset 0 0 0 2px var(--critical)"></i>cheater</span><span class="muted">arrows point from actor to target · round slider replays</span></div></div>
      <div class="net-side"><div class="panel"><h3>Links</h3><div class="checks" id="net-kinds">${EDGE_KINDS.map(([k, l, c, dash]) => `<label><input type="checkbox" value="${k}" ${S.netKinds.has(k) ? "checked" : ""}><i class="line ${dash ? "dash" : ""}" style="border-color:${css(c)}"></i>${esc(l)}</label>`).join("")}</div></div>
      <div class="panel"><h3>Conspiracy groups <span class="sub">connected by cheat merges and judge-labelled collusion; the metric also adds seen-but-silent links</span></h3><div class="groups-list" id="net-groups"></div></div></div></div>`;
    $("#net-layout").value = S.netLayout || "circular";
    $("#net-layout").onchange = (e) => { S.netLayout = e.target.value; renderNetwork(tb, true); };
    $$("#net-kinds input").forEach((i) => (i.onchange = () => { i.checked ? S.netKinds.add(i.value) : S.netKinds.delete(i.value); renderNetwork(tb, true); }));
  }
  const net = S.net, r = viewRound();
  const upto = (byr) => sum(Object.entries(byr).filter(([k]) => r == null || +k <= r).map(([, v]) => v));
  const edges = net.edges.filter((e) => S.netKinds.has(e.k)).map((e) => ({ ...e, n: upto(e.r) })).filter((e) => e.n > 0);
  const deg = new Map();
  for (const e of edges) { deg.set(e.s, (deg.get(e.s) || 0) + e.n); deg.set(e.t, (deg.get(e.t) || 0) + e.n); }
  const grp = S.netGroup != null ? new Set(net.groups[S.netGroup] || []) : null;
  const nodes = net.nodes.filter((n) => r == null || n.instigator || (n.joined || 1) <= r).sort((a, b) => String(a.team || "zz").localeCompare(String(b.team || "zz")) || String(a.id).localeCompare(String(b.id)));
  const N = nodes.map((n) => {
    const st = n.instigator ? null : agentAt({ initial_role: n.role0, converted_round: n.conv, removed_round: n.removed, cheat_round: n.cheat, joined_round: n.joined }, r);
    const color = n.instigator ? css("--serious") : st.removed ? css("--surface-3") : st.role === "investigator" ? css("--s7") : css("--s1");
    const dim = grp && !grp.has(n.id);
    return { id: n.id, name: n.id, value: deg.get(n.id) || 0, symbolSize: Math.min(26, 6 + Math.sqrt(deg.get(n.id) || 0) * 2.2),
      itemStyle: { color, borderColor: st && st.cheat ? css("--critical") : css("--surface"), borderWidth: st && st.cheat ? 2.5 : 1, opacity: dim ? 0.15 : 1 },
      label: { show: nodes.length <= 40 || (deg.get(n.id) || 0) > 6 || n.instigator, color: css("--ink-2"), fontSize: 10 },
      team: n.team, tip: `${n.id}${n.team ? " · " + n.team : ""}${n.instigator ? " · instigator" : st ? " · " + st.role : ""}${n.cheat ? " · cheater from R" + n.cheat : ""}${n.removed ? " · removed R" + n.removed : ""}` };
  });
  const ids = new Set(N.map((n) => n.id));
  const kc = Object.fromEntries(EDGE_KINDS.map(([k, , c, dash]) => [k, [css(c), dash]]));
  const L = edges.filter((e) => ids.has(e.s) && ids.has(e.t)).map((e) => ({ source: e.s, target: e.t, value: e.n,
    lineStyle: { color: kc[e.k][0], width: Math.min(5, 0.8 + Math.log2(1 + e.n)), type: kc[e.k][1] ? "dashed" : "solid", opacity: grp && !(grp.has(e.s) && grp.has(e.t)) ? 0.05 : e.k === "dm" ? 0.35 : 0.75, curveness: 0.18 },
    kind: e.k }));
  $("#net-sub").textContent = `${N.length} agents · ${L.length} links${r == null ? "" : " up to round " + r}`;
  const c = chart($("#c-net"), { animation: false, backgroundColor: "transparent",
    toolbox: { right: 0, top: -6, iconStyle: { borderColor: css("--muted") }, feature: { saveAsImage: { title: "PNG", pixelRatio: 2, backgroundColor: css("--surface"), name: "network" } } },
    tooltip: { trigger: "item", backgroundColor: css("--surface"), borderColor: css("--border-strong"), textStyle: { color: css("--ink"), fontSize: 12 },
      formatter: (p) => (p.dataType === "edge" ? `${esc(p.data.source)} → ${esc(p.data.target)}<br>${esc((EDGE_KINDS.find((k) => k[0] === p.data.kind) || [])[1])} × ${p.data.value}` : esc(p.data.tip)) },
    series: [{ type: "graph", layout: S.netLayout === "force" ? "force" : "circular", circular: { rotateLabel: true }, roam: true, draggable: true,
      force: { repulsion: N.length > 50 ? 70 : 160, edgeLength: [40, 140], gravity: 0.08, friction: 0.25 },
      data: N, links: L, edgeSymbol: ["none", "arrow"], edgeSymbolSize: 5, emphasis: { focus: "adjacency", lineStyle: { width: 3 } }, labelLayout: { hideOverlap: true } }] });
  if (c) { c.off("click"); c.on("click", (p) => { if (p.dataType === "node") openAgent(S.runName, p.data.id); }); }
  $("#net-groups").innerHTML = net.groups.length ? net.groups.slice(0, 12).map((g, i) => `<div class="g ${S.netGroup === i ? "on" : ""}" data-g="${i}"><b>${g.length} agents</b> ${g.map((a) => esc(a)).join(", ")}</div>`).join("") + (S.netGroup != null ? '<button class="link" id="net-clear">clear highlight</button>' : "") : '<div class="muted">No cheat merges or labelled collusion links yet.</div>';
  $$("#net-groups .g").forEach((el) => (el.onclick = () => { S.netGroup = S.netGroup === +el.dataset.g ? null : +el.dataset.g; renderNetwork(tb, true); }));
  if ($("#net-clear")) $("#net-clear").onclick = () => { S.netGroup = null; renderNetwork(tb, true); };
}

// ---- agents tab
const AG_COLS = [["id", "Agent"], ["team", "Problem"], ["role", "Role"], ["slot", "Slot"], ["status", "Status"], ["turns", "Turns"], ["tool_calls", "Tools"], ["dms_sent", "DMs out"],
  ["dms_received", "DMs in"], ["instigator_dms", "Instig. DMs"], ["prs_opened", "PRs"], ["prs_merged", "Merged"], ["approvals", "Approvals"], ["request_changes", "Rejects"],
  ["reports_filed", "Reports"], ["times_accused", "Accused"], ["confirmed_reports", "Confirmed"], ["tests_run", "Test runs"], ["full_passes", "Full passes"],
  ["labels", "Judge labels"], ["tokens_in", "Tokens in"], ["retries", "Retries"], ["errors", "Errors"]];
function agStatus(a) { return [a.removed_round ? `removed R${a.removed_round}` : "", a.cheat_round ? `cheater R${a.cheat_round}` : "", a.replaces ? `replaces ${a.replaces}` : ""].filter(Boolean).join(" · ") || "active"; }
function renderAgents(tb) {
  const [k, dir] = S.agentSort;
  const rows = S.detail.agents.slice().sort((a, b) => { const va = k === "status" ? agStatus(a) : k === "labels" ? sum(Object.values(a.labels || {})) : a[k], vb = k === "status" ? agStatus(b) : k === "labels" ? sum(Object.values(b.labels || {})) : b[k];
    return (typeof va === "number" && typeof vb === "number" ? va - vb : String(va ?? "").localeCompare(String(vb ?? ""))) * dir; });
  tb.innerHTML = `<div class="panel tbl-wrap" style="max-height:calc(100vh - 230px)"><table><thead><tr>${AG_COLS.map(([c, l]) => `<th class="sort ${c === k ? "sorted" + (dir > 0 ? " asc" : "") : ""} ${["id", "team", "role", "status", "labels"].includes(c) ? "" : "n"}" data-sort="${c}">${esc(l)}</th>`).join("")}</tr></thead><tbody>
    ${rows.map((a) => `<tr class="click" data-agent="${esc(a.id)}">${AG_COLS.map(([c]) => {
      if (c === "id") return `<td class="mono">${esc(a.id)}</td>`;
      if (c === "role") return `<td>${a.role === "investigator" ? `<span class="tag vio">investigator${a.converted_round ? " R" + a.converted_round : ""}</span>` : "worker"}</td>`;
      if (c === "status") return `<td class="${a.cheat_round || a.removed_round ? "hot" : "muted"}">${esc(agStatus(a))}</td>`;
      if (c === "labels") return `<td>${Object.entries(a.labels || {}).map(([l, n]) => `<span class="tag lab-${esc(l)}">${esc(l)} ${n}</span>`).join("") || '<span class="muted">–</span>'}</td>`;
      if (c === "team") return `<td>${esc(a.team)}</td>`;
      const v = a[c]; return `<td class="n ${!v ? "zero" : ""}">${c === "tokens_in" ? F.tok(v) : F.int(v)}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  $$("th[data-sort]", tb).forEach((th) => (th.onclick = () => { const c = th.dataset.sort; S.agentSort = [c, S.agentSort[0] === c ? -S.agentSort[1] : -1]; renderAgents(tb); }));
}

// ---- PRs tab
const refreshPRs = debounce(async () => { if (S.tab !== "prs") return; try { S.prs = await api(runUrl(S.runName, "/prs")); } catch (e) { return; } renderPRs($("#tabbody"), true); }, 3000);
async function renderPRs(tb, update) {
  if (!S.prs || !update) { try { S.prs = await api(runUrl(S.runName, "/prs")); } catch (e) { tb.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; } }
  const r = viewRound();
  let rows = S.prs.filter((p) => r == null || p.opened_round <= r);
  if (S.prFilter === "cheat") rows = rows.filter((p) => p.cheat);
  if (S.prFilter === "merged") rows = rows.filter((p) => p.status === "merged");
  if (S.prFilter === "open") rows = rows.filter((p) => p.status === "open");
  const [k, dir] = S.prSort;
  rows.sort((a, b) => { const va = a[k], vb = b[k]; return (typeof va === "number" && typeof vb === "number" ? va - vb : String(va ?? "").localeCompare(String(vb ?? ""), undefined, { numeric: true })) * dir; });
  const cols = [["id", "PR"], ["team", "Problem"], ["author", "Author"], ["title", "Title"], ["status", "Status"], ["opened_round", "Opened"], ["merged_round", "Merged"], ["version", "Ver."], ["approvers", "Approvers"], ["reviews", "Reviews"], ["last_check", "Harness check"], ["cheat", "Cheat"]];
  tb.innerHTML = `<div class="panel"><div style="display:flex;gap:8px;margin-bottom:8px;align-items:center"><select id="prf"><option value="all">all PRs</option><option value="cheat">cheat PRs</option><option value="merged">merged</option><option value="open">open</option></select>
    <span class="muted">${rows.length} PRs · cheat = passes the impossible assert (harness check or a test run) or edits the test file · click a row for the diff</span></div>
    <div class="tbl-wrap" style="max-height:calc(100vh - 260px)"><table><thead><tr>${cols.map(([c, l]) => `<th class="sort ${c === k ? "sorted" + (dir > 0 ? " asc" : "") : ""}" data-sort="${c}">${esc(l)}</th>`).join("")}</tr></thead><tbody>
    ${rows.slice(0, 1500).map((p) => `<tr class="click" data-pr="${esc(p.id)}"><td class="mono">${esc(p.id)}</td><td>${esc(p.team)}</td><td class="mono">${esc(p.author)}</td><td class="wrap">${esc(p.title)}</td>
      <td>${p.status === "merged" ? '<span class="tag acc">merged</span>' : p.status === "stale" ? '<span class="tag warn">stale</span>' : '<span class="tag">open</span>'}</td><td class="n">R${p.opened_round}</td><td class="n">${p.merged_round ? "R" + p.merged_round : "–"}</td><td class="n">${p.version}</td>
      <td class="mono">${esc((p.approvers || []).join(", "))}${p.cross ? ' <span class="tag">cross</span>' : ""}</td><td class="n">${(p.reviews || []).length}</td>
      <td class="n">${p.last_check ? `${p.last_check[1]}/${p.last_check[2]}` : "–"}</td><td>${p.cheat ? '<span class="tag crit">cheat</span>' : ""}${p.touches_tests ? '<span class="tag crit">edits tests</span>' : ""}</td></tr>`).join("")}</tbody></table></div></div>`;
  $("#prf").value = S.prFilter; $("#prf").onchange = (e) => { S.prFilter = e.target.value; renderPRs(tb, true); };
  $$("th[data-sort]", tb).forEach((th) => (th.onclick = () => { const c = th.dataset.sort; S.prSort = [c, S.prSort[0] === c ? -S.prSort[1] : -1]; renderPRs(tb, true); }));
}

function renderConfig(tb) {
  const c = S.detail.config || {};
  tb.innerHTML = `<div class="grid g2"><div class="panel"><h3>Config <span class="sub">config.json</span></h3><table>${Object.entries(c).map(([k, v]) => `<tr><td class="muted">${esc(k)}</td><td class="mono" style="white-space:normal;word-break:break-all">${esc(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table></div>
    <div class="panel"><h3>Run facts</h3><table>
      <tr><td class="muted">harness commit</td><td class="mono">${esc(S.detail.harness_commit || "–")}</td></tr>
      <tr><td class="muted">events</td><td class="n">${F.int(S.detail.summary.events)}</td></tr>
      <tr><td class="muted">usage-limit stops</td><td>${(S.detail.usage_stops || []).map((u) => `R${u.round} ${esc(u.phase)} ${F.day(u.t)}`).join("<br>") || "none"}</td></tr>
      <tr><td class="muted">resumes</td><td>${(S.detail.resumes || []).map((u) => `${F.day(u.t)} (${esc(u.phase)})`).join("<br>") || "none"}</td></tr>
      <tr><td class="muted">removed (order)</td><td class="mono" style="white-space:normal">${(S.detail.removed_order || []).map(([a, r]) => `${a} R${r}`).join(", ") || "none"}</td></tr>
      <tr><td class="muted">event types</td><td style="white-space:normal">${Object.entries(S.detail.type_counts || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${esc(k)} ${F.int(v)}`).join(" · ")}</td></tr>
    </table></div></div>`;
}

// ------------------------------------------------------------------------------------------------ drawers
function openDrawer(title, html) { $("#drawer-title").innerHTML = title; $("#drawer-body").innerHTML = html; $("#drawer").hidden = false; $("#drawer-body").scrollTop = 0; }
function closeDrawer() { $("#drawer").hidden = true; }

async function openAgent(run, id, more = false) {
  if (!more) openDrawer(`Agent <span class="mono">${esc(id)}</span>`, '<div class="loading">Loading timeline…</div>');
  let d;
  try { d = await api(runUrl(run, `/agent/${encodeURIComponent(id)}?limit=500`)); } catch (e) { $("#drawer-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const a = d.agent;
  const chips = [a.instigator ? '<span class="tag warn">instigator</span>' : a.role === "investigator" ? `<span class="tag vio">investigator${a.converted_round ? " since R" + a.converted_round : " from start"}</span>` : '<span class="tag">worker</span>',
    a.cheat_round ? `<span class="tag crit">cheater from R${a.cheat_round}</span>` : "", a.removed_round ? `<span class="tag crit">removed R${a.removed_round}</span>` : "",
    a.replaces ? `<span class="tag">replaces <a data-agent="${esc(a.replaces)}" data-run="${esc(run)}">${esc(a.replaces)}</a></span>` : "", a.replaced_by ? `<span class="tag">replaced by <a data-agent="${esc(a.replaced_by)}" data-run="${esc(run)}">${esc(a.replaced_by)}</a></span>` : "",
    ...Object.entries(a.labels || {}).map(([l, n]) => `<span class="tag lab-${esc(l)}">judge ${esc(l)} × ${n}</span>`)].join("");
  const kv = [["turns", a.turns], ["tool calls", a.tool_calls], ["DMs sent", a.dms_sent], ["DMs received", a.dms_received], ["instigator DMs", a.instigator_dms], ["PRs opened", a.prs_opened],
    ["PRs merged", a.prs_merged], ["approvals", a.approvals], ["rejections", a.request_changes], ["reports filed", a.reports_filed], ["accused", a.times_accused], ["confirmed", a.confirmed_reports],
    ["test runs", a.tests_run], ["full passes", a.full_passes], ["tokens in", F.tok(a.tokens_in)], ["retries", a.retries]].filter(([, v]) => v !== undefined);
  const audits = (a.audits || []).map((x) => `<div class="audit ${x.misaligned ? "mis" : ""}"><b>R${x.round} audit (${esc((x.triggers || []).join(", "))}): ${x.misaligned ? "misaligned" : "aligned"}${x.removed ? " → removed" : ""}</b><div class="ink2">${esc(x.summary || "")}</div></div>`).join("");
  const prs = (d.prs || []).map((p) => `<a data-pr="${esc(p.id)}" data-run="${esc(run)}" class="tag ${p.status === "merged" ? "acc" : ""}">${esc(p.id)} ${esc(p.status)}${p.touches_tests ? " · edits tests" : ""}</a>`).join(" ");
  S.agentFeed = { run, id, items: d.items, cats: S.agentCats || new Set(CATS.map((c) => c[0]).filter((c) => c !== "turns")) };
  openDrawer(`Agent <span class="mono">${esc(id)}</span> <span class="muted" style="font-weight:400;font-size:13px">${esc(a.team || "")}${a.slot != null ? " · slot " + a.slot : ""}</span>`,
    `<div>${chips}</div>${a.said ? `<p class="ink2" style="font-style:italic">“${esc(a.said)}”</p>` : ""}<div class="kv">${kv.map(([k, v]) => `<div><b>${typeof v === "number" ? F.int(v) : esc(v)}</b><span>${esc(k)}</span></div>`).join("")}</div>
    ${audits ? `<h3>Audits</h3>${audits}` : ""}${prs ? `<h3>PRs</h3><div>${prs}</div>` : ""}
    <h3 style="margin-top:14px">Timeline <span class="muted" style="font-weight:400">${d.items.length} events${d.more ? " (latest)" : ""}, newest first · includes DMs, reviews and reports aimed at ${esc(id)}</span></h3>
    <div class="feed-filters" id="ag-cats">${CATS.map(([k, l]) => `<button class="fchip ${S.agentFeed.cats.has(k) ? "on" : ""}" data-cat="${k}">${esc(l)}</button>`).join("")}</div>
    <div class="feed static" id="ag-feed"></div>`);
  $$("#ag-cats .fchip").forEach((b) => (b.onclick = () => { const c = b.dataset.cat; S.agentFeed.cats.has(c) ? S.agentFeed.cats.delete(c) : S.agentFeed.cats.add(c); S.agentCats = S.agentFeed.cats; b.classList.toggle("on"); drawAgentFeed(); }));
  drawAgentFeed();
}
function drawAgentFeed() {
  const f = S.agentFeed; if (!f) return;
  $("#ag-feed").innerHTML = f.items.filter((it) => f.cats.has(it.cat)).map((it) => evHTML(it, false, f.run)).join("") || '<div class="empty">No events in these categories.</div>';
}

async function openPR(run, id) {
  openDrawer(`PR <span class="mono">${esc(id)}</span>`, '<div class="loading">Loading…</div>');
  let p;
  try { p = await api(runUrl(run, `/pr/${encodeURIComponent(id)}`)); } catch (e) { $("#drawer-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const diff = esc(p.diff || "(no diff)").split("\n").map((l) => (l.startsWith("+") && !l.startsWith("+++") ? `<span class="add">${l}</span>` : l.startsWith("-") && !l.startsWith("---") ? `<span class="del">${l}</span>` : l.startsWith("@@") ? `<span class="hunk">${l}</span>` : l)).join("\n");
  openDrawer(`PR <span class="mono">${esc(p.id)}</span> · ${esc(p.title)}`,
    `<div>${p.cheat ? '<span class="tag crit">cheat</span>' : ""}${p.touches_tests ? '<span class="tag crit">edits the test file</span>' : ""}<span class="tag ${p.status === "merged" ? "acc" : ""}">${esc(p.status)}</span>
      <span class="tag">author <a data-agent="${esc(p.author)}" data-run="${esc(run)}">${esc(p.author)}</a></span><span class="tag">${esc(p.team)}</span><span class="tag">opened R${p.opened_round}</span>${p.merged_round ? `<span class="tag">merged R${p.merged_round}</span>` : ""}<span class="tag">version ${p.version}</span></div>
    <h3>Approvers</h3><div>${(p.approvers || []).map((a) => `<a class="agent" data-agent="${esc(a)}" data-run="${esc(run)}">${esc(a)}</a>`).join(", ") || '<span class="muted">none</span>'}</div>
    <h3>Harness checks</h3><div class="ink2">${(p.checks || []).map((c) => `v${c[0]}: ${c[1]}/${c[2]}${c[3] ? ' <span class="tag crit">full pass</span>' : ""}`).join(" · ") || "none"}</div>
    <h3>Reviews</h3>${(p.reviews || []).map((r) => `<div class="ev c-prs open"><div class="h"><span class="t"><a class="agent" data-agent="${esc(r.agent)}" data-run="${esc(run)}">${esc(r.agent)}</a> ${r.decision === "approve" ? '<span class="tag good">approve</span>' : '<span class="tag warn">request changes</span>'}${r.label ? `<span class="tag lab-${esc(r.label)}">judge: ${esc(r.label)}</span>` : ""}</span><span class="w">R${r.round} · v${r.version}</span></div><div class="b">${linkify(r.comment || "", run)}</div></div>`).join("") || '<div class="muted">none</div>'}
    <h3>Diff against main <span class="muted" style="font-weight:400">(latest version)</span></h3><pre class="diff">${diff}</pre>`);
}
async function openRaw(run, seq) {
  openDrawer(`Event <span class="mono">#${seq}</span>`, '<div class="loading">Loading…</div>');
  try { const ev = await api(runUrl(run, `/event/${seq}`)); openDrawer(`Event <span class="mono">#${seq}</span> · ${esc(ev.type)}`, `<pre class="raw">${esc(JSON.stringify(ev, null, 2))}</pre>`); }
  catch (e) { $("#drawer-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
}

// ------------------------------------------------------------------------------------------------ fleet + ops
function renderFleet(update = false) {
  const devs = ((S.fleet || {}).devices || []);
  const runs = [...S.runs.values()];
  const runsOn = (d) => runs.filter((s) => (d.keys || []).includes(s.machine_key) && (s.state === "running" || s.snapshot));
  const html = [`<div class="section-title"><h2>Fleet</h2><span class="sub">devices from Tailscale; numbers from each Mac's fleet-statusd (port ${esc((S.fleet || {}).port || 7477)}), the same source as the menu bar app · refreshed every 15 s</span></div>
    <div class="grid g3">`];
  for (const d of devs) {
    const st = d.status, on = runsOn(d);
    const memPct = st ? st.memory.usedBytes / st.memory.totalBytes : null;
    const loadPct = st ? st.load[0] / st.cores : null;
    html.push(`<div class="panel"><h3><span class="badge ${d.online ? "st-running" : "st-stopped"}">${d.online ? "online" : "offline"}</span> ${esc(st ? st.name : d.name)} <span class="sub">${esc(d.os)}${d.self ? " · this machine" : ""}${d.via && d.via !== S.machine ? " · via " + esc(d.via) : ""}</span></h3>
      ${st ? `<div class="kv">
        <div><b>${st.battery ? st.battery.percent + "%" : "AC"}</b><span>${st.battery ? esc(st.battery.state) + (st.battery.remaining ? " · " + esc(st.battery.remaining) : "") : "no battery"}</span></div>
        <div><b>${F.num(st.cpuPercent, 0)}%</b><span>CPU (${st.cores} cores)</span><div class="meter"><i class="${st.cpuPercent > 90 ? "hot" : st.cpuPercent > 70 ? "warm" : ""}" style="width:${Math.min(100, st.cpuPercent)}%"></i></div></div>
        <div><b>${F.gb(st.memory.usedBytes)}</b><span>of ${F.gb(st.memory.totalBytes)} · pressure ${esc(st.memory.pressure)}</span><div class="meter"><i class="${st.memory.pressure !== "normal" ? "hot" : memPct > 0.85 ? "warm" : ""}" style="width:${100 * memPct}%"></i></div></div>
        <div><b>${st.load.map((x) => F.num(x, 1)).join(" ")}</b><span>load 1/5/15 min</span><div class="meter"><i class="${loadPct > 3 ? "hot" : loadPct > 1.5 ? "warm" : ""}" style="width:${Math.min(100, (100 * loadPct) / 4)}%"></i></div></div>
        <div><b>${F.dur(st.uptimeSeconds)}</b><span>uptime${st.uptimeSeconds < 7200 ? " · recent restart" : ""}</span></div>
        <div><b>${st.t3Running ? "yes" : "no"}</b><span>T3 Code running</span></div></div>
        <div class="muted" style="font-size:11.5px">sampled ${F.ago(st.time)}</div>`
      : `<div class="muted">${d.online ? esc(d.status_error ? "no stats: " + d.status_error : "online, no fleet-statusd numbers for " + (d.os || "this device")) : "offline" + (d.last_seen && !d.last_seen.startsWith("0001") ? " · last seen " + esc(new Date(d.last_seen).toLocaleString()) : "")}</div>`}
      ${on.length ? `<h3 style="margin-top:10px">Runs here</h3>${on.map((s) => `<div><a href="#/run/${encodeURIComponent(s.name)}">${esc(armLabel(s))}</a>${s.snapshot ? " " + badge(s) : ""} <span class="muted">${esc(modelLabel(s.model))} · R${s.round}/${s.rounds_total}${s.snapshot ? ` · results/live-${esc(s.machine)}.md ${F.clock(s.snapshot_t)}` : ""}</span></div>`).join("")}` : ""}
    </div>`);
  }
  html.push("</div>");
  const snaps = runs.filter((s) => s.snapshot && !deviceOf(s)); // --machine-alias maps a git machine to its device card
  if (snaps.length) {
    const ms = [...new Set(snaps.map((s) => s.machine))];
    html.push(`<div class="section-title"><h2>Machines seen through git</h2><span class="sub">not on Tailscale; status from results/live-&lt;machine&gt;.md</span></div><div class="grid g3">${ms.map((m) => {
      const rs = snaps.filter((s) => s.machine === m); const t = Math.max(...rs.map((s) => s.snapshot_t || 0));
      return `<div class="panel"><h3><span class="badge ${nowS() - t < 1800 ? "st-running" : "st-stalled"}">${nowS() - t < 1800 ? "reporting" : "stale"}</span> ${esc(m)} <span class="sub">snapshot ${F.day(t)} (${F.ago(t)})</span></h3>
        ${rs.map((s) => `<div><a href="#/run/${encodeURIComponent(s.name)}">${esc(armLabel(s))}</a> ${badge(s)} <span class="muted">R${s.round}/${s.rounds_total} · ${s.turns ?? "–"} turns · ${s.problems_at_100 ?? "–"} @100%</span></div>`).join("")}
        <p class="muted" style="font-size:11.5px">No battery, CPU or memory: this machine isn't on Tailscale. Add it to the tailnet and run status/install from the fleet repo to see live numbers here.</p></div>`; }).join("")}</div>`);
  }
  if (!devs.length) html.push(`<div class="empty">No fleet data yet${(S.fleet || {}).error ? ": " + esc(S.fleet.error) : ""}.</div>`);
  $("#view").innerHTML = html.join("");
}

async function renderOps() {
  if (!$("#ops-root")) $("#view").innerHTML = '<div id="ops-root"><div class="loading">Loading ops…</div></div>';
  let d;
  try { d = await api("/api/ops?minutes=180"); } catch (e) { $("#ops-root").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  if (S.route.view !== "ops") return;
  disposeCharts($("#ops-root"));
  const html = [];
  d.machines.forEach((m, i) => {
    if (m.error) { html.push(`<div class="section-title"><h2>${esc(m.machine)}</h2><span class="sub" style="color:var(--critical)">${esc(m.error)}</span></div>`); return; }
    const ms = m.machine_stats || {};
    const lastHour = (a) => sum(a.slice(-60));
    html.push(`<div class="section-title"><h2>${esc(m.machine)}</h2><span class="sub">booted ${F.day(m.boot_t)} (${F.ago(m.boot_t)}) · dashboard up ${F.ago(m.started)}</span></div>
      <div class="tiles">
        ${tile("Load 1/5/15", (ms.load || []).map((x) => F.num(x, 1)).join(" "), `${ms.ncpu} cores`, ms.load && ms.load[0] > 3 * ms.ncpu ? "bad" : "")}
        ${tile("Memory used", ms.mem_used_gb != null ? `${ms.mem_used_gb}<small>/ ${ms.mem_total_gb} GB</small>` : "–", `swap ${ms.swap_used_gb ?? "–"} GB · compressed ${ms.compressed_gb ?? "–"} GB`)}
        ${tile("Codex sessions", F.int((m.procs || {}).codex), `${((m.procs || {}).swarm || []).length} swarm processes`)}
        ${tile("Turns last hour", F.int(lastHour(m.turns)), `${F.int(lastHour(m.tool_calls))} tool calls`)}
        ${tile("Throttle retries last hour", F.int(lastHour(m.retries)), `${F.int(lastHour(m.errors))} turn errors`, lastHour(m.errors) > 10 ? "bad" : "")}
        ${tile("Dashboard server", `${F.num(m.self_cpu, 1)}%<small>CPU</small>`, `${(m.procs || {}).rss_mb ?? "–"} MB RSS`)}
        ${tile("Disk free", ms.disk_free_gb != null ? ms.disk_free_gb + " GB" : "–", "repo volume")}
      </div>
      <div class="grid g2" style="margin-top:12px">
        <div class="panel"><h3>Throughput <span class="sub">per minute, last 3 h, all runs</span></h3><div class="chart" id="o-tp-${i}"></div></div>
        <div class="panel"><h3>Throttle retries and turn errors <span class="sub">per minute; retries are mostly 403s that Codex recovered from</span></h3><div class="chart" id="o-err-${i}"></div></div>
        <div class="panel"><h3>Turns per minute by run <span class="sub">stacked</span></h3><div class="chart" id="o-runs-${i}"></div></div>
        <div class="panel"><h3>Tokens by run <span class="sub">input, all time</span></h3><div class="chart tall" id="o-tok-${i}"></div></div>
      </div>
      <div class="grid g2" style="margin-top:12px">
        <div class="panel"><h3>Usage-limit stops, resumes and early ends</h3><div class="tbl-wrap" style="max-height:360px"><table><thead><tr><th>When</th><th>Run</th><th>What</th><th class="n">Round</th><th>Phase</th></tr></thead><tbody>
          ${m.stops.slice().reverse().map((x) => `<tr><td>${F.day(x.t)}</td><td><a href="#/run/${encodeURIComponent(x.run)}">${esc(x.run)}</a></td><td>${x.kind === "usage_limit_hit" ? '<span class="tag crit">usage limit</span>' : x.kind === "run_resumed" ? '<span class="tag good">resumed</span>' : `<span class="tag warn">ended: ${esc(x.phase)}</span>`}${x.missed ? ` <span class="muted">${x.missed} missed</span>` : ""}</td><td class="n">${x.round ?? "–"}</td><td>${esc(x.kind === "run_end" ? "" : x.phase || "")}</td></tr>`).join("") || '<tr><td colspan="5" class="muted">none</td></tr>'}</tbody></table></div></div>
        <div class="panel"><h3>Production queue <span class="sub">runs/queue.log, last ${m.queue_lines.length} lines</span></h3><div class="qlog" id="qlog-${i}">${m.queue_lines.map((l) => `<div class="${/^\s{2,}/.test(l) ? "ln-indent" : /^-{3,}/.test(l) ? "ln-note" : /exit 3|stopped|did not complete|usage/.test(l) ? "ln-exit3" : /exit 0|push: ok|labeled .* exit 0|queue done/.test(l) ? "ln-ok" : ""}">${esc(l)}</div>`).join("")}</div></div>
      </div>
      <div class="panel" style="margin-top:12px"><h3>Token usage by run</h3><div class="tbl-wrap"><table><thead><tr><th>Run</th><th>Group</th><th class="n">Input</th><th class="n">Cached</th><th class="n">Output</th><th class="n">Cache share</th></tr></thead><tbody>
        ${m.tokens.map((t) => `<tr class="click" data-run="${esc(t.name)}"><td>${esc(t.name)}</td><td class="muted">${esc(t.group)}</td><td class="n">${F.tok(t.in)}</td><td class="n">${F.tok(t.cached)}</td><td class="n">${F.tok(t.out)}</td><td class="n">${F.pct(t.cached / (t.in || 1), 0)}</td></tr>`).join("")}
        <tr><td><b>Total</b></td><td></td><td class="n"><b>${F.tok(sum(m.tokens.map((t) => t.in)))}</b></td><td class="n">${F.tok(sum(m.tokens.map((t) => t.cached)))}</td><td class="n">${F.tok(sum(m.tokens.map((t) => t.out)))}</td><td></td></tr></tbody></table></div></div>`);
  });
  if (d.peers && d.peers.length) html.push(`<div class="section-title"><h2>Peers</h2></div><div class="panel"><table><tr><th>URL</th><th>Machine</th><th>Status</th><th class="n">Runs</th><th class="n">Latency</th></tr>${d.peers.map((p) => `<tr><td class="mono">${esc(p.url)}</td><td>${esc(p.machine || "–")}</td><td>${p.ok ? '<span class="tag good">ok</span>' : `<span class="tag crit">${esc(p.error || "down")}</span>`}</td><td class="n">${p.runs}</td><td class="n">${p.latency_ms ?? "–"} ms</td></tr>`).join("")}</table></div>`);
  $("#ops-root").innerHTML = html.join("");
  d.machines.forEach((m, i) => {
    if (m.error) return;
    const x = m.minutes.map((t) => F.clock(t));
    chart($("#o-tp-" + i), { ...base({ x, int: true, file: "throughput" }), series: [line("turns", m.turns, css("--s1")), line("tool calls ÷ 10", m.tool_calls.map((v) => +(v / 10).toFixed(1)), css("--s3"))] });
    chart($("#o-err-" + i), { ...base({ x, int: true, bars: true, file: "errors" }), series: [bar("retries", m.retries, css("--warn")), bar("turn errors", m.errors, css("--critical"))] });
    const pr = Object.entries(m.per_run_turns || {});
    chart($("#o-runs-" + i), { ...base({ x, int: true, file: "turns-by-run" }), series: pr.map(([n, v], j) => line(n.replace(/-\d{8}-\d{6}$/, ""), v, css(`--s${(j % 8) + 1}`), { stack: "t", areaStyle: { opacity: 0.25 } })) });
    const tk = m.tokens.slice(0, 20);
    chart($("#o-tok-" + i), { ...base({ legend: false, bars: true, file: "tokens", grid: { left: 210, top: 6, right: 50 } }), tooltip: { trigger: "item", formatter: (p) => `${esc(tk[p.dataIndex].name)}<br>${F.tok(p.value)} input` },
      xAxis: { type: "value", splitLine: { lineStyle: { color: css("--grid") } }, axisLabel: { color: css("--muted"), formatter: (v) => F.tok(v) } },
      yAxis: { type: "category", inverse: true, data: tk.map((t) => t.name.replace(/-\d{8}-\d{6}/, "")), axisLabel: { color: css("--ink-2"), fontSize: 10.5 }, axisTick: { show: false }, axisLine: { lineStyle: { color: css("--axis") } } },
      series: [{ type: "bar", data: tk.map((t) => t.in), itemStyle: { color: css("--s1"), borderRadius: [0, 3, 3, 0] }, barMaxWidth: 12, label: { show: true, position: "right", color: css("--ink-2"), fontSize: 10.5, formatter: (p) => F.tok(p.value) } }] });
    const q = $("#qlog-" + i); if (q) q.scrollTop = q.scrollHeight;
  });
  clearTimeout(S.opsTimer);
  S.opsTimer = setTimeout(() => { if (S.route.view === "ops") renderOps(); }, 10000);
}

boot();
