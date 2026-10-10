"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const api = async (u, o) => { const r = await fetch(u, o); if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText); return r.json(); };
const nice = k => k === "-" ? "Startup check" : k.replace(/^\d+_/, "").replace(".sh", "").replace(/_/g, " ");

const DEMO = [
  ["Prepare", "Creating folders and settings for this run."],
  ["New identity", "Choosing a fresh hostname and SSH version for the honeypot."],
  ["Start", "Starting the honeypot and the packet recorder together."],
  ["Attack", "A separate attacker machine scans the honeypot, guesses passwords, and logs in by hand."],
  ["Stop recording", "Closing the packet recording cleanly so the file is complete."],
  ["Save log", "Checking and archiving the honeypot's own record of what happened."],
  ["Match", "Linking each honeypot session to its network conversation."],
  ["Save", "Writing the results to files you can download."],
];
const CMP = [
  ["Start", "Starting the honeypot with its original identity."],
  ["Scan before", "Scanning it the way an attacker would."],
  ["New identity", "Picking a new hostname and SSH version."],
  ["Restart", "Restarting the honeypot with the new identity."],
  ["Scan after", "Scanning it again."],
];

/* ---------- navigation ---------- */
function show() {
  const v = (location.hash || "#run").slice(1);
  const view = ["run", "identity", "sessions", "evidence"].includes(v) ? v : "run";
  document.querySelectorAll(".view").forEach(e => e.hidden = e.id !== "view-" + view);
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("on", a.dataset.view === view));
  if (view === "identity") loadCompare(); else if (view !== "run") loadResults();
}
addEventListener("hashchange", show);

/* ---------- hex chains ---------- */
function build(el, steps) { el.innerHTML = steps.map((s, i) => `<li data-i="${i + 1}"><span class="hex">${i + 1}</span><span>${s[0]}</span></li>`).join(""); }
function paint(el, step, state) {
  el.querySelectorAll("li").forEach(li => {
    const i = +li.dataset.i;
    li.className = state === "done" ? "done" : i < step ? "done" : i === step ? (state === "failed" ? "failed" : "active") : "";
  });
}
build($("#chain"), DEMO); build($("#cmpchain"), CMP);

/* ---------- run state from the server ---------- */
const logEl = $("#log");
function addLine(t) {
  if (logEl.firstElementChild && logEl.firstElementChild.classList.contains("muted")) logEl.textContent = "";
  const span = document.createElement("span");
  if (/^==\s*\d+\/\d+/.test(t)) span.className = "step";
  else if (/FAILED|\[warn\]|Error/.test(t)) span.className = "bad";
  span.textContent = t + "\n";
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;
}
function dispatch(d) {
  const running = d.state === "running";
  document.querySelectorAll("#runbtn,#resetbtn,#cmpbtn").forEach(b => b.disabled = running);
  if (d.mode === "compare") {
    $("#cmpbtn").textContent = running ? "Comparing..." : "Compare again";
    $("#cmptitle").textContent = running ? `Step ${d.step} of 5` : d.state === "done" ? "Finished" : d.state === "failed" ? "The comparison stopped with an error" : "Ready to compare";
    $("#cmpsub").textContent = running && CMP[d.step - 1] ? CMP[d.step - 1][1] : d.state === "failed" ? "Open the Run page and read the log to see what went wrong." : d.state === "done" ? "Both scans are below. The version string is what an attacker would fingerprint." : "Starts the honeypot, scans it, changes its identity, restarts it and scans it again.";
    paint($("#cmpchain"), d.step, d.state);
  } else if (d.mode === "reset") {
    $("#runbtn").textContent = "Run demo";
    $("#runtitle").textContent = running ? "Stopping the lab" : d.state === "done" ? "Lab stopped. Ready to run" : "Could not stop the lab";
    paint($("#chain"), 0, "idle"); $("#stepnote").textContent = "";
  } else {
    $("#runbtn").textContent = running ? "Running..." : d.state === "idle" ? "Run demo" : "Run again";
    $("#runtitle").textContent = running ? `Step ${d.step} of 8` : d.state === "done" ? "Finished" : d.state === "failed" ? "The run stopped with an error" : "Ready to run";
    $("#runsub").textContent = d.state === "failed" ? "Read the last lines of the log to see what went wrong, then run again." :
      d.state === "done" ? "Open Sessions to see who did what." : "One click starts the whole lab, attacks it, and matches what the honeypot saw with what the network saw.";
    paint($("#chain"), d.step, d.state);
    $("#stepnote").textContent = running && DEMO[d.step - 1] ? DEMO[d.step - 1][1] : "";
  }
}
let es = null;
function follow(since = 0) {
  if (es) es.close();
  es = new EventSource("/api/run/stream?since=" + since);
  es.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.line !== undefined && d.mode !== "compare") addLine(d.line);
    dispatch(d);
    if (d.state === "done" || d.state === "failed") { es.close(); es = null; refreshAll(); if (d.mode === "compare") loadCompare(); }
  };
}
async function launch(url, mode) {
  logEl.innerHTML = "";
  if (mode === "compare") { $("#cmpraw").textContent = ""; paint($("#cmpchain"), 0, "running"); } else paint($("#chain"), 0, "running");
  try { await api(url, { method: "POST" }); follow(0); }
  catch (err) { addLine("Could not start: " + err.message); if (mode === "compare") $("#cmptitle").textContent = "Could not start: " + err.message; }
}
$("#runbtn").onclick = () => launch("/api/run", "demo");
$("#cmpbtn").onclick = () => launch("/api/compare", "compare");
$("#resetbtn").onclick = () => launch("/api/reset", "reset");
$("#logtoggle").onclick = e => { const h = logEl.hidden = !logEl.hidden; e.target.textContent = h ? "Show" : "Hide"; };

/* ---------- lab + identity ---------- */
window.__nmapVersion = null;
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("#labchips").innerHTML = `<span class="chip"><i class="dot ${s.docker ? "up" : "down"}"></i>Docker ${s.docker ? "ready" : "not reachable"}</span>`;
    $("#identity").innerHTML = `<dt>Hostname</dt><dd>${esc(s.hostname || "not set")}</dd><dt>SSH banner</dt><dd>${esc(s.banner || "not set")}</dd>` +
      (window.__nmapVersion ? `<dt>Scanner reads</dt><dd>${esc(window.__nmapVersion)}</dd>` : "");
    const roles = { cowrie: "The honeypot", capture: "Records every packet", attacker: "Plays the attacker" };
    $("#lab").innerHTML = ["cowrie", "capture", "attacker"].map(n => {
      const c = s.containers.find(x => x.name === n), up = c && c.state === "running";
      return `<li><i class="dot ${up ? "up" : ""}"></i><span>${n}</span><span class="role">${roles[n]}${up ? "" : " (stopped)"}</span></li>`;
    }).join("");
  } catch { $("#labchips").innerHTML = `<span class="chip"><i class="dot down"></i>Server not reachable</span>`; }
}

/* ---------- identity comparison ---------- */
async function loadCompare() {
  let r; try { r = await api("/api/compare"); } catch { return; }
  $("#cmp-empty").hidden = r.available; $("#cmp-body").hidden = !r.available;
  if (!r.available) return;
  const card = k => {
    const d = r[k], o = r.before, after = k === "after";
    const chg = f => after && d[f] !== o[f] ? "changed" : "";
    return `<div class="card ${k}"><h3>${after ? "After" : "Before"}<span class="tag">${after ? "new identity" : "original identity"}</span></h3>
      <p class="muted small" style="margin:0">What a scanner reads</p><div class="big ${chg("version")}">${esc(d.version || "no answer")}</div>
      <dl class="kv"><dt>Hostname</dt><dd class="${chg("hostname")}">${esc(d.hostname || "not recorded")}</dd><dt>SSH banner</dt><dd class="${chg("banner")}">${esc(d.banner || "not recorded")}</dd></dl></div>`;
  };
  $("#cmpcards").innerHTML = card("before") + card("after");
  $("#cmptabs").innerHTML = ["before", "after"].map((k, i) => `<button role="tab" aria-selected="${i === 0}" data-k="${k}">Raw scan, ${k}</button>`).join("");
  const sh = k => { $("#cmpraw").textContent = r[k].raw; $("#cmptabs").querySelectorAll("button").forEach(b => b.setAttribute("aria-selected", b.dataset.k === k)); };
  $("#cmptabs").onclick = e => { if (e.target.dataset.k) sh(e.target.dataset.k); };
  sh("before");
}

/* ---------- results ---------- */
let last = null;
async function loadResults() {
  try { last = await api("/api/results"); } catch { return; }
  window.__nmapVersion = last.nmap_version;
  const none = !last.available;
  $("#sess-empty").hidden = !none; $("#sess-body").hidden = none;
  if (none) return;
  const c = last.counts, n = last.sessions.length;
  $("#tiles").innerHTML =
    `<div class="tile"><b>${n}</b><span>Sessions recorded</span></div>` +
    `<div class="tile ok"><b>${c.matched || 0}</b><span>Matched to packets</span></div>` +
    `<div class="tile warn"><b>${c.partial || 0}</b><span>Partly matched</span></div>` +
    `<div class="tile bad"><b>${c.unmatched || 0}</b><span>Not matched</span></div>`;
  $("#sessions tbody").innerHTML = last.sessions.map(s => {
    const cmds = (s.commands || []).filter(Boolean);
    return `<tr><td class="m">${esc(s.session_id.slice(0, 12))}</td><td>${esc(nice(s.scenario))}</td>` +
      `<td class="m">${s.src_port}</td><td>${s.failed_logins}</td><td title="${esc(cmds.join(" | "))}">${cmds.length}</td><td>${s.packets}</td>` +
      `<td><span class="badge ${esc(s.status)}">${esc(s.status[0].toUpperCase() + s.status.slice(1))}</span></td></tr>`;
  }).join("");
  $("#perscen").innerHTML = `<div class="scen">` + Object.entries(last.per_scenario).map(([k, v]) =>
    `<div><span>${esc(nice(k))}</span><span>${v.sessions} session${v.sessions === 1 ? "" : "s"}<small>${v.commands} command${v.commands === 1 ? "" : "s"}, ${v.failed_logins} failed login${v.failed_logins === 1 ? "" : "s"}</small></span></div>`).join("") + `</div>`;
  const po = last.pcap_only || [];
  $("#pcaponly").innerHTML = po.length
    ? `<p class="muted small" style="margin-top:0">Connections that reached the honeypot but never became a logged session, such as port scans. Only the network recording sees these.</p><div class="scen">` +
      po.map(p => `<div><span style="font-family:var(--mono)">${esc(p.src_ip)}:${p.src_port}</span><span>${p.packets} packets<small>${p.bytes} bytes</small></span></div>`).join("") + `</div>`
    : `<p class="muted">Every connection in the recording became a honeypot session.</p>`;
  const names = Object.keys(last.scenario_logs);
  $("#logtabs").innerHTML = names.map((k, i) => `<button role="tab" aria-selected="${i === 0}" data-k="${esc(k)}">${esc(nice(k))}</button>`).join("");
  const showLog = k => { $("#evlog").textContent = last.scenario_logs[k] || ""; $("#logtabs").querySelectorAll("button").forEach(b => b.setAttribute("aria-selected", b.dataset.k === k)); };
  $("#logtabs").onclick = e => { if (e.target.dataset.k) showLog(e.target.dataset.k); };
  if (names.length) showLog(names[0]);
  $("#pcapnote").textContent = last.pcap ? `Packet recording from the last run: ${last.pcap}. Open it in Wireshark from the data/pcap folder.` : "";
}
function refreshAll() { refreshStatus().then(loadResults).then(refreshStatus); }

/* ---------- start-up: resume if a run is already going ---------- */
(async () => {
  show();
  await loadResults(); await refreshStatus();
  try {
    const r = await api("/api/run");
    if (r.state === "running") { dispatch(r); follow(0); }
    else if (r.state === "done" || r.state === "failed") dispatch(r);
  } catch {}
  setInterval(refreshStatus, 8000);
})();
