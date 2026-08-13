# CoreSentinel API & Integration Protocol

> **Four surfaces, one service layer.** The CLI, the HTTP API, the MCP server and the
> dashboard parse requests and render responses. They decide nothing.

---

## 🎯 The Guarantee

> **The same operation, through any surface, produces the same audit record.**

A surface that reached past the service layer into storage or an engine could write without
emitting, and an unaudited write through a side door makes the whole trail a statement about
one entrance. So the boundary is enforced structurally: a test walks the import graph and
fails the build if `coresentinel_core/api/` or `coresentinel_core/mcp/` imports storage or an
engine module directly.

Routes and MCP tools are both **generated from the service catalogue**, so an operation
cannot exist on one surface and be missing from another.

---

## 🌐 HTTP API

```bash
coresentinel serve                         # loopback, port 7878
coresentinel serve --host 0.0.0.0          # refused without a configured token
coresentinel serve --port 9000 --threaded
```

Versioned from birth: every route is `/api/v1/<area>/<verb>`, and `GET /api/v1` returns the
catalogue.

| | Rule |
| :--- | :--- |
| **Bind** | Loopback by default. A non-loopback bind **without a configured token is refused at startup** — not at the first request. Auto-generating one there would satisfy the check while leaving an unauthenticated governance system on the network. |
| **Writes** | Always require the token, on any interface. A local server is reachable by every process on the machine. |
| **Reads** | Open over loopback; token required from anywhere else. |
| **Method** | A write must be POSTed. `GET` on a write operation is `405`. |
| **Errors** | `{"error": {"code": "...", "message": "...", "remedy": "..."}}` — machine-readable codes, never a stack trace. |

```bash
curl http://127.0.0.1:7878/api/v1/health/get
curl -X POST http://127.0.0.1:7878/api/v1/memory/store \
  -H "X-CoreSentinel-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"layer":"project","fact":"Uses PostgreSQL","confidence":0.98,"source":"compose"}'
```

`http.server` is single-threaded and is not a production web server. It is here because
CoreSentinel is local-first and a dependency for one JSON endpoint would not earn its place.
`--threaded` is available when a dashboard needs concurrent reads.

---

## 🖥️ Dashboard

`coresentinel serve` also serves the dashboard at `http://127.0.0.1:7878/`. No build step,
no npm, no framework: three files — `index.html`, `app.css`, `app.js` — shipped inside the
package.

| | Rule |
| :--- | :--- |
| **Reach** | The page is a client of `/api/v1` like any other. It cannot import an engine or open the store, because a browser has no other way into the process. |
| **Allowlist** | Only the three shipped filenames resolve. Every other path — including `..` — is a `404`, so the asset route cannot be walked into a file read. |
| **Policy** | Served with `default-src 'self'; connect-src 'self'; frame-ancestors 'none'` and `X-Content-Type-Options: nosniff`. Nothing loads from a remote origin. |
| **Reads only** | Every operation the page calls is a read. The dashboard shows the system; it does not drive it. |
| **No sample data** | Not one figure ships in the assets. A dashboard with a fixture behind a view renders beautifully while the thing it claims to show is broken. |

Seven views — Overview, Project, Agents, Memory, Decisions, Audit, Health — each declaring
the operations it reads in `data-endpoints`, which a test checks against the catalogue.

**When the API stops answering, every panel says so in place.** No panel keeps its last
number: a dashboard that renders after its source is gone is a dashboard that lies. That is
the same rule the engines keep — a check that cannot run is `UNKNOWN`, not a pass.

---

## 🔌 MCP Server

```bash
coresentinel mcp             # JSON-RPC 2.0 over stdio
coresentinel mcp --tools     # list the surface without starting the server
```

Implements `initialize`, `tools/list`, `tools/call` and `ping`. Tools are named
`area_verb` and generated from the catalogue.

**stdout carries protocol frames and nothing else.** Every diagnostic goes to stderr — one
stray print corrupts the stream and the host sees a protocol error instead of the message
that caused it. That is the same contract the CLI has kept since v1.

A **service refusal is a tool result, not a protocol error**: the model needs to read why it
was refused and act on it, which it cannot do with a JSON-RPC error code.

```json
{"result": {"isError": true,
            "content": [{"type": "text", "text": "UNKNOWN_AGENT: unknown agent 'Nobody'"}]}}
```

The server's `initialize` response carries instructions telling the host to call
`context_assemble` before starting work, `decision_verify` before reversing an architectural
choice, and that a verification result of `UNKNOWN` is not a pass.

---

## 📋 Operations

Every operation is available on all three surfaces. Writes are marked; each emits an event,
and auditing is a subscriber, so emitting is how a change gets recorded.

| Area | Read | Write |
| :--- | :--- | :--- |
| **project** | `inspect`, `list` | |
| **memory** | `search`, `brief` | `store` |
| **context** | `assemble` | |
| **decision** | `search`, `verify` | `create` |
| **agent** | `list`, `permissions`, `status` | `dispatch` |
| **task** | `list` | `run` |
| **gate** | `status` | `run` |
| **verification** | | `run` |
| **health** | `get` | |
| **review** | `run` | |
| **incident** | `list` | `create` |
| **pattern** | `search` | |
| **audit** | `list`, `verify` | `record` |
| **knowledge** | `query` | |

---

## 🔧 Building Integrations In Governed Projects

The guidance below concerns webhooks and third-party integrations **inside the projects
CoreSentinel governs** — it is not about CoreSentinel's own API.

### Webhook Security & Idempotency
- **Signature Verification**: Always validate incoming webhook headers/signatures (e.g.
  HMAC-SHA256) before processing any payload.
- **Idempotency Guard**: Store `event_id` in a tracking table with a unique index. Skip
  already-processed events cleanly with `200 OK`.
- **Async Ingestion**: Fast-return `200 OK` within 500ms; push processing to background workers.

### Vendor Resilience
- **Exponential Backoff** with random jitter for failed HTTP requests.
- **Rate Limit Handling**: Respect `Retry-After` and `HTTP 429`. Never loop aggressively.
- **Circuit Breaker**: Auto-pause outbound requests after consecutive vendor failures.

### Secret Protection
- **Encrypted Storage**: Encrypt vendor secrets at rest.
- **Proactive Token Refresh**: Refresh 5 minutes before expiry to avoid mid-operation 401s.
- **Zero Raw Secrets in Logs**: Sanitize `Authorization` and `X-API-Key` before logging.
