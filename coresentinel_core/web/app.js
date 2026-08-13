/* CoreSentinel dashboard.

   Every panel calls /api/v1 and renders what comes back. There is no sample data
   in this file, and there is nothing to fall back to when a call fails: a panel
   that cannot reach its endpoint says so, in place, instead of showing the last
   number it happened to have.

   That is the same rule the rest of CoreSentinel keeps. A verification check that
   cannot run reports UNKNOWN rather than passing; a discovery dimension nothing
   evidenced reports unknown rather than empty; a panel whose source is gone
   reports that rather than a figure. */

"use strict";

const API = "/api/v1";

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
};

const state = { view: "overview", offline: false };

/* ---------------------------------------------------------------- transport */

async function call(operation, params) {
  const path = `${API}/${operation.replace(/\./g, "/")}`;
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  const response = await fetch(path + query, { headers: { Accept: "application/json" } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (payload.error && payload.error.message) || `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return payload.result;
}

function goOffline(detail) {
  state.offline = true;
  document.getElementById("offline").hidden = false;
  document.getElementById("offline-detail").textContent = detail ? ` ${detail}` : "";
}

function goOnline() {
  state.offline = false;
  document.getElementById("offline").hidden = true;
}

/* Render one panel. A failure is shown in the panel it belongs to, never
   swallowed and never replaced with a plausible-looking default. */
async function panel(host, title, load, render, span) {
  const card = el("section", `card ${span || ""}`.trim());
  card.appendChild(el("h2", null, title));
  const body = el("div", "loading", "loading…");
  card.appendChild(body);
  host.appendChild(card);

  try {
    const data = await load();
    goOnline();
    body.className = "";
    body.textContent = "";
    render(body, data);
  } catch (error) {
    body.className = "failed";
    body.textContent = `could not load: ${error.message}`;
    if (error instanceof TypeError) goOffline("The server is unreachable.");
  }
  return card;
}

/* ---------------------------------------------------------------- helpers */

function statusClass(value) {
  const text = String(value || "").toUpperCase();
  if (["HEALTHY", "PASS", "INTACT", "APPROVED", "VERIFIED", "CLEAR", "COMPLETED",
       "RESOLVED", "ACCEPTED"].includes(text)) return "ok";
  if (["WARNING", "PENDING", "PENDING_REVIEW", "OBSERVED", "PROPOSED",
       "RELATED"].includes(text)) return "warn";
  if (["CRITICAL", "FAIL", "FAILED", "TAMPERED", "BLOCKED", "DENIED",
       "UNVERIFIED", "REVIEW REQUIRED", "OPEN"].includes(text)) return "bad";
  return "unknown";
}

function pill(value) {
  return el("span", `pill ${statusClass(value)}`, value == null ? "unknown" : value);
}

function rows(host, entries) {
  if (!entries.length) {
    host.appendChild(el("p", "empty", "nothing recorded"));
    return;
  }
  const list = el("div", "rows");
  entries.forEach(([label, value, basis]) => {
    const row = el("div", "row");
    const left = el("div", "label");
    left.appendChild(label instanceof Node ? label : el("span", null, label));
    if (basis) left.appendChild(el("span", "basis", basis));
    row.appendChild(left);
    const right = el("div", "value");
    right.appendChild(value instanceof Node ? value : el("span", null, value));
    row.appendChild(right);
    list.appendChild(row);
  });
  host.appendChild(list);
}

function table(host, headers, records) {
  if (!records.length) {
    host.appendChild(el("p", "empty", "nothing recorded"));
    return;
  }
  const wrap = el("div", "scroll");
  const node = el("table");
  const head = el("thead");
  const headRow = el("tr");
  headers.forEach((h) => headRow.appendChild(el("th", null, h)));
  head.appendChild(headRow);
  node.appendChild(head);

  const body = el("tbody");
  records.forEach((cells) => {
    const row = el("tr");
    cells.forEach((cell) => {
      const td = el("td");
      td.appendChild(cell instanceof Node ? cell : el("span", null, cell == null ? "—" : cell));
      row.appendChild(td);
    });
    body.appendChild(row);
  });
  node.appendChild(body);
  wrap.appendChild(node);
  host.appendChild(wrap);
}

function meter(value, tone) {
  const bar = el("div", `meter ${tone}`);
  const fill = el("span");
  fill.style.width = `${Math.max(0, Math.min(100, Number(value) || 0))}%`;
  bar.appendChild(fill);
  return bar;
}

/* ---------------------------------------------------------------- views */

const views = {};

views.overview = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  await Promise.all([
    panel(grid, "Project health", () => call("health.get"), (body, data) => {
      const stat = el("div", "stat");
      stat.appendChild(el("span", `figure ${statusClass(data.status)}`,
        data.overall_score === null ? "n/a" : data.overall_score));
      stat.appendChild(el("span", "unit", data.overall_score === null ? "" : "/ 100"));
      body.appendChild(stat);
      body.appendChild(pill(data.status));
      if (data.unknown_dimensions && data.unknown_dimensions.length) {
        body.appendChild(el("p", "note",
          `Not evidenced: ${data.unknown_dimensions.join(", ")}. An unknown dimension is not an empty one.`));
      }
    }, "third"),

    panel(grid, "Audit chain", () => call("audit.verify"), (body, data) => {
      const stat = el("div", "stat");
      stat.appendChild(el("span", `figure ${statusClass(data.verdict)}`, data.checked));
      stat.appendChild(el("span", "unit", "records"));
      body.appendChild(stat);
      body.appendChild(pill(data.verdict));
      if (data.note) body.appendChild(el("p", "note", data.note));
    }, "third"),

    panel(grid, "Quality gates", () => call("gate.status"), (body, data) => {
      const counts = {};
      Object.values(data.gates).forEach((g) => {
        counts[g.status] = (counts[g.status] || 0) + 1;
      });
      rows(body, Object.entries(counts).map(([status, n]) => [pill(status), `${n}`]));
    }, "third"),

    panel(grid, "Gate pipeline", () => call("gate.status"), (body, data) => {
      table(body, ["gate", "status", "code", "reason"],
        data.pipeline.map((name) => {
          const gate = data.gates[name] || {};
          return [name, pill(gate.status), el("span", "mono", gate.code || "—"),
                  gate.reason || "—"];
        }));
    }, "half"),

    panel(grid, "Recent activity", () => call("audit.list", { limit: 8 }), (body, data) => {
      table(body, ["subject", "actor", "action", "at"],
        data.records.map((r) => [el("span", "mono", r.subject), r.actor,
                                 String(r.action || "").slice(0, 48), r.recorded_at]));
    }, "half"),

    panel(grid, "Decisions", () => call("decision.search"), (body, data) => {
      rows(body, data.decisions.slice(0, 6).map((d) =>
        [`${d.id} — ${d.title}`, pill(d.status), d.reason]));
    }, "half"),

    panel(grid, "Incidents", () => call("incident.list"), (body, data) => {
      const s = data.summary;
      body.appendChild(el("p", "note", `${s.total} recorded, ${s.open} still open`));
      rows(body, data.incidents.slice(0, 6).map((i) =>
        [`${i.id} — ${i.title}`, pill(i.status), i.learning || "no learning recorded"]));
      if (s.without_learning && s.without_learning.length) {
        body.appendChild(el("p", "note",
          `Resolved with no learning: ${s.without_learning.join(", ")}. A fix stops it now; a learning stops it recurring.`));
      }
    }, "half"),
  ]);
};

views.project = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  await Promise.all([
    panel(grid, "What CoreSentinel understands", () => call("project.inspect", { verbose: "1" }),
      (body, data) => {
        body.appendChild(el("p", "note",
          `${data.scanned_files} file(s) scanned in ${data.duration_ms} ms`));
        rows(body, Object.entries(data.dimensions).map(([name, detail]) => {
          if (!detail.known) return [name, el("span", "pill unknown", "unknown")];
          const evidence = detail.findings
            .map((f) => `${f.value}: ${f.evidence.file} (${f.evidence.locator})`)
            .join(" · ");
          return [name, detail.values.join(", "), evidence];
        }));
        if (data.unknown_dimensions.length) {
          body.appendChild(el("p", "note",
            "An unknown dimension is not an empty one — nothing proved it either way."));
        }
      }, "half"),

    panel(grid, "Knowledge graph", () => call("knowledge.query"), (body, data) => {
      rows(body, [
        ["entities", `${data.entities}`],
        ["relations", `${data.relations}`],
        ["dangling edges", `${data.dangling}`],
      ]);
      body.appendChild(el("h3", null, "by type"));
      rows(body, Object.entries(data.by_type || {}).map(([k, v]) => [k, `${v}`]));
      body.appendChild(el("p", "note",
        "Edges come only from recorded relationships. Nothing is inferred from source code."));
    }, "half"),
  ]);
};

views.agents = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  await Promise.all([
    panel(grid, "Contracts", () => call("agent.list"), (body, data) => {
      table(body, ["agent", "role", "authority"],
        data.agents.map((a) => [el("strong", null, a.name), a.role, a.authority]));
    }, "half"),

    panel(grid, "Enforced permissions", () => call("agent.permissions"), (body, data) => {
      rows(body, [
        ["contracts declaring permissions", `${data.declared.length} / ${data.total}`],
        ["defaulted to read-only", data.defaulted.length ? data.defaulted.join(", ") : "none"],
      ]);
      const holders = Object.entries(data.escalation_holders || {});
      if (holders.length) {
        body.appendChild(el("h3", null, "may request escalation"));
        rows(body, holders.map(([agent, granted]) => [agent, granted.join(", ")]));
      }
      body.appendChild(el("p", "note",
        "Permissions are enforced by a sandbox, not merely declared: an ungranted operation fails at the point of use and the denial is audited."));
    }, "half"),

    panel(grid, "Recent tasks", () => call("task.list", { limit: 15 }), (body, data) => {
      table(body, ["agent", "objective", "status"],
        data.tasks.map((t) => [t.agent, String(t.objective || "").slice(0, 64),
                               pill(t.status)]));
    }),
  ]);
};

views.memory = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  const search = el("section", "card half");
  search.appendChild(el("h2", null, "Search memory"));
  const input = el("input");
  input.type = "search";
  input.placeholder = "postgres migration";
  input.setAttribute("aria-label", "Search memory");
  search.appendChild(input);
  const results = el("div");
  results.style.marginTop = "12px";
  search.appendChild(results);
  grid.appendChild(search);

  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const query = input.value.trim();
      results.textContent = "";
      if (!query) return;
      results.className = "loading";
      results.textContent = "searching…";
      try {
        const data = await call("memory.search", { query, limit: 12 });
        results.className = "";
        results.textContent = "";
        results.appendChild(el("p", "note", `${data.count} hit(s)`));
        rows(results, data.results.map((hit) => [
          hit.text,
          hit.confidence == null ? el("span", "pill unknown", hit.kind)
                                 : el("span", `pill ${hit.confidence >= 0.9 ? "ok" : "warn"}`,
                                      hit.confidence),
          `${hit.layer}/${hit.scope} · ${hit.source || "no source"}`,
        ]));
      } catch (error) {
        results.className = "failed";
        results.textContent = `could not search: ${error.message}`;
      }
    }, 220);
  });

  await panel(grid, "Session briefing", () => call("memory.brief"), (body, data) => {
    rows(body, [
      ["last task", data.working.current_task],
      ["status", data.working.status],
      ["bound project", data.scope.bound_project || "unbound — core scope"],
    ]);
    body.appendChild(el("h3", null, "established facts"));
    rows(body, (data.established || []).map((f) =>
      [f.fact, el("span", "pill ok", f.confidence), `${f.layer} · ${f.source || ""}`]));
    body.appendChild(el("h3", null, "needs verification"));
    rows(body, (data.needs_verification || []).map((f) =>
      [f.fact, el("span", "pill bad", f.confidence), f.layer]));
    body.appendChild(el("h3", null, "stale"));
    rows(body, (data.stale || []).map((f) =>
      [f.fact, el("span", "pill warn", `${f.age_days}d`), f.layer]));
  }, "half");
};

views.decisions = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  const check = el("section", "card");
  check.appendChild(el("h2", null, "Would this change reverse a decision?"));
  const input = el("input");
  input.type = "text";
  input.placeholder = "switch from Redis to database sessions";
  input.setAttribute("aria-label", "Proposed change");
  check.appendChild(input);
  const verdict = el("div");
  verdict.style.marginTop = "12px";
  check.appendChild(verdict);
  grid.appendChild(check);

  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const change = input.value.trim();
      verdict.textContent = "";
      verdict.className = "";
      if (!change) return;
      try {
        const data = await call("decision.verify", { change });
        verdict.textContent = "";
        const head = el("p");
        head.appendChild(pill(data.verdict));
        head.appendChild(el("span", "note", ` checked ${data.considered} accepted decision(s)`));
        verdict.appendChild(head);
        rows(verdict, data.findings.map((f) => [
          `${f.decision_id} — ${f.title}`,
          pill(f.verdict),
          `${f.detail}${f.reason ? " · recorded reason: " + f.reason : ""}`,
        ]));
      } catch (error) {
        verdict.className = "failed";
        verdict.textContent = `could not check: ${error.message}`;
      }
    }, 260);
  });

  await panel(grid, "Decision ledger", () => call("decision.search"), (body, data) => {
    table(body, ["id", "title", "chosen", "alternatives", "status", "reason"],
      data.decisions.map((d) => [
        el("span", "mono", d.id), d.title, d.chosen,
        (d.alternatives || []).join(", ") || "—", pill(d.status), d.reason,
      ]));
  });
};

views.audit = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  await Promise.all([
    panel(grid, "Chain integrity", () => call("audit.verify"), (body, data) => {
      body.appendChild(pill(data.verdict));
      rows(body, [
        ["chained records", `${data.checked}`],
        ["legacy (never signed)", `${data.legacy}`],
        ["written around the ledger", `${data.unchained || 0}`],
      ]);
      (data.problems || []).forEach((p) => {
        body.appendChild(el("p", "failed", `${p.code} — ${p.record}: ${p.detail}`));
      });
      body.appendChild(el("p", "note",
        "Tamper-evidence, not tamper-proofing: anyone with write access can recompute the chain. What they cannot do is change one record and leave the rest intact."));
    }, "third"),

    panel(grid, "Trail", () => call("audit.list", { limit: 40 }), (body, data) => {
      table(body, ["seq", "subject", "actor", "action", "result", "at"],
        data.records.map((r) => [
          el("span", "mono", r.seq == null ? "legacy" : r.seq),
          el("span", "mono", r.subject), r.actor,
          String(r.action || "").slice(0, 52),
          r.result ? pill(r.result) : "—", r.recorded_at,
        ]));
    }),
  ]);
};

views.health = async (host) => {
  const grid = el("div", "grid");
  host.appendChild(grid);

  await panel(grid, "Health dimensions, and what evidences them", () => call("health.get"),
    (body, data) => {
      const stat = el("div", "stat");
      stat.appendChild(el("span", `figure ${statusClass(data.status)}`,
        data.overall_score === null ? "n/a" : data.overall_score));
      stat.appendChild(el("span", "unit",
        data.overall_score === null
          ? "too few dimensions could be evaluated"
          : `/ 100 — mean of ${data.known_dimensions} evaluable dimension(s)`));
      body.appendChild(stat);

      Object.entries(data.dimensions).forEach(([name, score]) => {
        const seen = (data.coverage || {})[name] || {};
        const heading = el("h3", null,
          `${name} — ${score === null ? "unknown" : score + "/100"}` +
          (seen.total && seen.evaluated !== seen.total
            ? ` (${seen.evaluated} of ${seen.total} signals)` : ""));
        body.appendChild(heading);
        if (score !== null) body.appendChild(meter(score, statusClass(score >= 90 ? "HEALTHY" : score >= 75 ? "WARNING" : "CRITICAL")));
        rows(body, ((data.signals || {})[name] || []).map((s) => [
          s.signal,
          el("span", `pill ${s.met === true ? "ok" : s.met === false ? "bad" : "unknown"}`,
             s.met === true ? "met" : s.met === false ? "not met" : "not evaluable"),
          `${s.basis}${s.detail ? " — " + s.detail : ""}`,
        ]));
      });

      body.appendChild(el("p", "note",
        "Every signal states its basis: the command that produced it, or the filesystem measurement it read. A signal that cannot be evaluated here is not counted as met."));
    });
};

/* ---------------------------------------------------------------- shell */

async function show(name) {
  state.view = name;
  document.querySelectorAll(".tab").forEach((tab) => {
    if (tab.dataset.view === name) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view").forEach((section) => {
    section.hidden = section.id !== `view-${name}`;
  });

  const host = document.getElementById(`view-${name}`);
  host.textContent = "";
  await views[name](host);
  document.getElementById("fetched").textContent =
    `fetched ${new Date().toLocaleTimeString()}`;
}

async function boot() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => show(tab.dataset.view));
  });
  document.getElementById("refresh").addEventListener("click", () => show(state.view));

  try {
    const response = await fetch(API, { headers: { Accept: "application/json" } });
    const catalogue = await response.json();
    document.getElementById("version").textContent = catalogue.coresentinel_api;
  } catch (error) {
    goOffline("The catalogue could not be read.");
  }

  try {
    const project = await call("project.inspect");
    document.getElementById("target").textContent = project.project.root;
  } catch (error) {
    /* The banner already says the API is unreachable; the path is not worth a
       second identical complaint. */
  }

  await show("overview");
}

document.addEventListener("DOMContentLoaded", boot);
