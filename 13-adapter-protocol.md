# 🔌 CoreSentinel Host Adapter Protocol

> **Vendor-Neutral AI Infrastructure Layer**
> CoreSentinel does not care which AI coding assistant is being used. One Core, many hosts.

---

## 🧭 Architecture

```text
                        CoreSentinel Core
          (Memory · Governance · Context · Verification · Telemetry)
                                │
                      CoreSentinel Adapter Layer
                                │
   ┌──────────┬──────────┬──────┴─────┬──────────┬──────────┐
   ↓          ↓          ↓            ↓          ↓          ↓
Claude Code  Cursor   Gemini CLI    Codex    Copilot    Windsurf
```

The Core is the single source of truth. Adapters are **projections** of that Core onto each host's
native rules transport — never forks of it. A host is added by registering an adapter in
[`adapters.json`](./adapters.json); no Core logic changes.

---

## 📦 The Five Core Services

Every host consumes the same five services. What differs is only the **channel**:

| Service | Contract | Backing Store |
| :--- | :--- | :--- |
| **Memory** | 6-layer facts with confidence classification | `memory/*.json` |
| **Governance** | Protocols, quality gates, anti-pattern rules, evolution policy | `*.md`, `anti-patterns.json` |
| **Context** | Identity, squad contracts, protocol index | `00-identity.md`, `squad-contracts.json` |
| **Verification** | Evidence-Based Verification Suite (pass ≥ 80/100) | `coresentinel verify` |
| **Telemetry** | Token spend & session analytics | `agent-usage-log.json` |

**Channel values:** `native` (host built-in) · `file` (rendered rules file) · `cli` (shell-out to `coresentinel`) · `none` (unsupported by host).

---

## 🤖 Registered Host Adapters

| Host | Vendor | Format | Global Bind Target |
| :--- | :--- | :--- | :--- |
| **Claude Code** | Anthropic | `markdown` | `~/.claude/CLAUDE.md` |
| **Cursor IDE** | Anysphere | `mdc` | `~/.cursor/rules/coresentinel.mdc` |
| **Gemini CLI** | Google | `markdown` | `~/.gemini/GEMINI.md` |
| **OpenAI Codex** | OpenAI | `markdown` | `~/.codex/AGENTS.md` |
| **Google Antigravity** | Google | `markdown` | `~/.antigravity/AGENTS.md` |
| **GitHub Copilot** | GitHub | `markdown` | *(project scope only)* `.github/copilot-instructions.md` |
| **Windsurf** | Codeium | `markdown` | `~/.codeium/windsurf/memories/global_rules.md` |
| **Generic Agent** | Open Standard | `markdown` | *(project scope only)* `AGENTS.md` |

---

## 🛡️ Sync Safety Rules

Syncing writes to files **outside** the CoreSentinel repository, so the adapter layer enforces:

1. **Dry run by default.** `sync` previews the payload and target path. Nothing is written without `--apply`.
2. **Managed-file marker.** Every generated file opens with `<!-- CORESENTINEL:MANAGED -->`.
3. **No silent overwrite.** If the target exists and lacks that marker, the sync is **BLOCKED**. Hand-authored host rules are never clobbered.
4. **Forced writes are backed up.** `--force` copies the original to `<file>.coresentinel.bak` before replacing it.
5. **Compact profiles.** Hosts with rules-file size limits (Windsurf) receive a trimmed Core without the full protocol index.

---

## 🌐 The Context Bundle (CoreSentinel API)

`coresentinel adapter export --json` emits one normalized, host-agnostic payload — the contract any
agent, IDE plugin, or CI job consumes without knowing anything about CoreSentinel's file layout:

```json
{
  "coresentinel_api": "1.0",
  "host": { "active": "claude-code", "installed": ["claude-code", "cursor"] },
  "identity": { "name": "Iris", "role": "Universal coding agent" },
  "governance": { "protocols": 34, "anti_pattern_rules": 12, "quality_gates": { "Security": "PASS" } },
  "memory": { "layers": { "project": 2, "patterns": 4 }, "confidence_thresholds": { "known": 0.9 } },
  "verification": { "command": "coresentinel verify", "pass_threshold": 80 },
  "telemetry": { "command": "coresentinel stats" }
}
```

---

## ⚡ CLI Commands

```bash
# List every registered host adapter with the capability matrix
coresentinel adapter list

# Scan the machine for installed / currently-active AI coding hosts
coresentinel adapter detect

# Inspect a single adapter card (bind targets, service channels, host extensions)
coresentinel adapter show claude-code

# Preview the Core rendered into a host's native format (dry run — writes nothing)
coresentinel adapter sync cursor

# Bind the Core into the host for real
coresentinel adapter sync cursor --apply

# Bind at project scope instead of global
coresentinel adapter sync copilot --scope project --apply

# Replace an existing hand-authored rules file (backs it up first)
coresentinel adapter sync gemini-cli --apply --force

# Emit the host-agnostic context bundle
coresentinel adapter export
coresentinel adapter export --json
```

---

## ➕ Registering a New Host

Append an entry to `adapters.json` — no Python changes required:

```json
{
  "id": "my-agent",
  "name": "My Agent",
  "vendor": "Acme",
  "surface": "CLI",
  "transport": "rules_file",
  "format": "markdown",
  "global_path": "~/.myagent/RULES.md",
  "project_path": "./RULES.md",
  "detect": ["~/.myagent"],
  "detect_env": ["MYAGENT_SESSION"],
  "capabilities": {
    "memory": "file", "governance": "file", "context": "file",
    "verification": "cli", "telemetry": "none"
  },
  "extensions": ["MCP Servers"],
  "notes": "Short operational caveat for this host."
}
```

If the host needs a non-markdown wrapper, add a branch to `render_for_adapter()` in
[`coresentinel_adapters.py`](./coresentinel_adapters.py) keyed on the `format` field.
