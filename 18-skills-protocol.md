# Skill Layer Protocol (`Iris skills`)
> "A protocol says what to check. A skill is a tool that checks it. Bind them or the tool never runs."

The host (Claude Code) ships executable **skills** — packaged instruction sets invoked
by name. CoreSentinel shipped eleven versions without referencing a single one, so
every skill the host offered went unused while the protocols described the same work
in prose. This protocol binds the two layers.

**Trigger**: session start (read the inventory), and every phase gate in
[Team Protocol](./02-team-protocol.md).

---

## 1. Skill vs Agent vs Protocol

Three different things, routinely confused:

| Layer | What it is | Who runs it | State |
|---|---|---|---|
| **Protocol** (this repo) | The standard — what "correct" means | Iris reads it | Persistent, versioned |
| **Skill** (host) | An executable procedure the host loads on demand | Iris invokes by name | Stateless per call |
| **Agent** (subagent) | A separate context that reports back | Iris delegates to it | Forgets everything after |

A skill is **not** one of the 17 specialists. Invoking `/code-review` does not
discharge Cato and Sage — it is the instrument they use. Coverage is still measured in
agents, never in skills run.

---

## 2. Inventory — verified available this host

Checked against the live skill listing. Nothing below is aspirational.

### Bound to a phase gate (run these)

| Skill | Binds to | Phase | Owner |
|---|---|---|---|
| `code-review` | [35-review-protocol.md](./35-review-protocol.md) | 5 — Review | Cato, Sage |
| `simplify` | [35-review-protocol.md](./35-review-protocol.md) | 5 — Review | Sage |
| `security-review` | [40-security-protocol.md](./40-security-protocol.md) | 6 — Security | Argus, Cipher, Aegis |
| `run` | [25-test-protocol.md](./25-test-protocol.md) | 4 — Test | Probe |
| `init` | [05-init-protocol.md](./05-init-protocol.md) | 0 — Intake | Iris |
| `claude-api` | [17-ai-protocol.md](./17-ai-protocol.md) | 1, 3 | Kai, Scout |
| `artifact-design` | [52-handoff-protocol.md](./52-handoff-protocol.md) | 8 — Ship | Iris |
| `artifact-diagramming` | [52-handoff-protocol.md](./52-handoff-protocol.md) | 8 — Ship | Iris |
| `artifact-capabilities` | [52-handoff-protocol.md](./52-handoff-protocol.md) | 8 — Ship | Iris |
| `dataviz` | [12-health-score-protocol.md](./12-health-score-protocol.md) | any reporting | Ledger |
| `design` | [20-design-protocol.md](./20-design-protocol.md) | **2 — Design** (Screen Brief reference, UI/flow canvases), 8 — Ship | Vera, Luna |
| `claude-in-chrome` | [20-design-protocol.md](./20-design-protocol.md) | 4 — Test (screenshot every changed screen, 1280 + 390) | Probe, Vera |

**Host availability — tested 2026-09-04:** `claude-in-chrome` is now **listed** on darwin
(it was absent 2026-08-20), but listed is not the same as working. Tested this session:

| Layer | State |
|---|---|
| Skill + `mcp__claude-in-chrome__*` tools | Present |
| Chrome extension connection | **Not connected** — every call fails |
| `file://` URLs | Refused outright, even when connected |

So Phase 4's screenshot step is **conditional on the extension being connected**, not on the
skill appearing in the listing. Check by calling `tabs_context_mcp` once; if it reports the
extension is not connected, say so and fall back — `run` for E2E, {USER_NAME}'s own eyes for
the design pass. Never report a screenshot that was not taken.

**To screenshot a local file at all**, serve it over HTTP first
(`python3 -m http.server <port>` in its directory) — `file://` is rejected by the extension.

### Harness maintenance (run when the condition fires, not on a schedule)

| Skill | Use when |
|---|---|
| `update-config` | {USER_NAME} asks for an automated behaviour ("from now on, whenever X"), a permission change, or an env var. **Memory cannot satisfy a "whenever X" request — only a hook can.** Pairs with `install-hooks.sh`. |
| `fewer-permission-prompts` | Permission prompts are interrupting a long run |
| `keybindings-help` | Keybinding changes only |
| `loop` | A recurring check on an interval ("poll the deploy every 5 min") |
| `schedule` | A cron-scheduled cloud agent, or a one-time future run |

### Reference-only (read before answering, never as a build step)

| Skill | Rule |
|---|---|
| `claude-api` | **Mandatory read** before touching anything Claude/Anthropic-shaped — model IDs, pricing, tool use, caching. Never answer from memory. Skip only when another provider (OpenAI/Gemini/Llama/…) is the subject. |
| `claude-code-guide` (agent) | Questions about Claude Code, the Agent SDK, or the Claude API. Delegate rather than guess. |

---

## 3. Invocation Discipline

1. **Bind, don't duplicate.** When a skill covers a checklist section, invoke it and
   review its findings — do not hand-walk the checklist in parallel and report twice.
2. **The checklist survives the skill.** `code-review` and `security-review` are
   generic; the stack-specific items in 35 and 40 (payment callbacks, tenant scoping,
   framework upload methods) are ours and still get checked by hand.
3. **A skill's finding is a candidate, not a verdict.** Confirm it in the code before
   reporting it to {USER_NAME}. Tool output is evidence, not truth.
4. **Never report a skill you did not run.** Same rule as Phase 8 persistence —
   "ran the review" with no findings list is where silent no-ops hide.
5. **Read before the first line of output**, for the three mandatory-read skills
   (`claude-api`, `artifact-design`, `dataviz`). Reading them after writing the code
   is the same as not reading them.

---

## 4. What Iris Cannot Invoke

Recorded so no future session wastes a turn trying:

- **`/code-review ultra`** (alias `/ultrareview`) — a billed, user-triggered cloud
  review. {USER_NAME} launches it; Iris cannot, not via Bash and not via any tool.
  When a diff warrants it, **recommend it and stop** — do not attempt it.
- **Workflows / multi-agent orchestration** — only on {USER_NAME}'s explicit request.
  The Full-Squad rule in [02-team-protocol.md](./02-team-protocol.md) mandates agent
  *coverage*; it does not authorise spawning a workflow fleet.
- **Skills not in the listing.** The listing is the whole set. A `/name` that is not
  there does not exist — do not guess at one.

---

## 5. Gap Register

Open gaps between what the protocols assume and what the host actually provides.
Reviewed at Phase 8.

| Gap | Status |
|---|---|
| No CoreSentinel skill exists — `coresentinel verify` runs via Bash only | Open. A packaged skill would make the 6-point suite invocable by name and installable by other users ([public-use goal](./00-identity.md)). |
| 17 squad specialists are prose roles, not agent definitions | Open. Only `muse` exists in `~/.claude/agents/`. Roles are played in-context, which is valid but means "parallel" in Phase 3/5/6 is sequential in practice. Say so honestly in gate reports. |
| `claude-in-chrome` named in Phase 4 but not installed | Open (2026-08-20, darwin). E2E browser journeys have no instrument; `run` covers app-level only. |
| Two conflicting 17-agent rosters | See [02-team-protocol.md](./02-team-protocol.md) § Roster Authority. |

---

## 6. Session-Start Checklist

At the top of any project session, Iris confirms in one line:

```
Skills: <n> available | bound: code-review, security-review, run, claude-api
Host: <os> | shell: <zsh/pwsh> | python: <python3/python>
```

If the listing has changed since this protocol was written, **update this file first**,
then work. An inventory nobody maintains is worse than none — it reports confidence
in tools that may no longer be there.
