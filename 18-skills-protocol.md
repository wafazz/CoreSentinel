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
| `landing-design` | [21-landing-protocol.md](./21-landing-protocol.md) | **2 — Design** (Landing Brief), 4 — Test, 5 — Review | Vera, Luna |

**`landing-design` is CoreSentinel's own — the first skill this system ships rather than consumes.**
Installed at `~/.claude/skills/landing-design/` (`SKILL.md` + `references/{scales,sections,tells}.md`),
written 2026-09-10. **Confirmed listed and invocable 2026-09-11 (win32)** — the restart the previous
note was waiting on has happened.

Two things separate it from every other row above. It is the only skill here whose **first step is
reading the project** — schema, routes, plans, roles, components — rather than applying a rule set in
a vacuum. And it is the only one covering the **public** surface: everything else in this table, and
all of `20-design-protocol.md`, is authenticated console work with an inverted rule set.

**Surface routing — never cross these:**

| Target | Protocol | Skill |
|---|---|---|
| Console, dashboard, admin, any authenticated screen | `20-design-protocol.md` | `design` |
| Landing, marketing site, pricing, public template | `21-landing-protocol.md` | `landing-design` |

A hero, generous vertical rhythm and a pricing CTA are **tells** on a console (`20` §2) and are the
job on a landing page (`21` §3). Console density on a public page is the same error reversed. Ask
which surface the brief is for before reaching for either.

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
(`python3 -m http.server <port>` in its directory; `python -m http.server` on Windows) —
`file://` is rejected by the extension.

**Host availability — win32, 2026-09-11:** all 13 bound skills above are present in the listing,
`landing-design` included. `claude-in-chrome` was **tested this session and the extension IS
connected** — `tabs_context_mcp` answered "No tab group exists" (a connected extension reporting an
empty group, not a connection failure). So the darwin "Not connected" row above is stale as a
general claim: it was that machine, that day. Phase 4 screenshots are reachable on win32.

What still holds on both hosts: `file://` is refused, so a local page must be served over HTTP
first. And a screenshot of an authenticated screen needs the dev server up and a seeded login —
that cost is the real reason a Phase 4 screenshot gets skipped, not the extension. Say which of the
two it was; never report a screenshot that was not taken.

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
| `workflow-authoring` | Read only when {USER_NAME} has already asked for a workflow. It is the script reference for the Workflow tool — **it does not authorise running one** (§4). Added to this inventory 2026-09-11 (win32). |

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
| No CoreSentinel skill exists — `coresentinel verify` runs via Bash only | **Partly closed 2026-09-10.** `landing-design` is now the first CS-authored skill (§2), proving the packaging shape works. `coresentinel verify` itself is still Bash-only — that one stays open. |
| Landing pages had no protocol — four lines in `20-design-protocol.md` §6.6 | **Closed 2026-09-10** by [21-landing-protocol.md](./21-landing-protocol.md) + the `landing-design` skill. |
| No landing-page **reference artifact** — `references/dashboard-benchmark.html` has no public-surface twin | **Open.** `20-design-protocol.md` §1 is emphatic that design converges against an image and essentially never from prose, and `21` §2 makes a reference mandatory in every brief — but there is nothing in-repo to point at, so briefs must borrow an external URL. The console side solved this and the public side has not. |
| Skills were only ever hand-authored | **Partly closed 2026-09-10.** `coresentinel_core/learning/skills.py` drafts a `SKILL.md` from clustered trusted knowledge (≥ 3 lessons in one context, ≥ 8 observations behind them) into `memory/skill_candidates/`. It **never writes to `~/.claude/skills/`** — CoreSentinel does not own that surface, and installing a skill changes how an agent approaches every matching task, which is a person's decision. `evolve review` lists the drafts. |
| A drafted skill has nobody reviewing it | **Open.** Drafts accumulate in `memory/skill_candidates/` and only `evolve review` mentions them. Until one is actually read and installed, the pipeline's last step is unexercised — and a draft nobody reads is a draft that rots. |
| 17 squad specialists are prose roles, not agent definitions | Open. Only `muse` exists in `~/.claude/agents/`. Roles are played in-context, which is valid but means "parallel" in Phase 3/5/6 is sequential in practice. Say so honestly in gate reports. |
| `claude-in-chrome` named in Phase 4 but not installed | **Closed 2026-09-11 (win32)** — skill listed and the extension connected, so Phase 4 screenshots are reachable. It was genuinely absent on darwin 2026-08-20 and listed-but-unconnected there 2026-09-04; treat availability as **per host**, check it with one `tabs_context_mcp` call, and say which host you checked. See §2. |
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
