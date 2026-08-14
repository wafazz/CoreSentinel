# ⬆️ Upgrading to CoreSentinel v2 (`11.0.0`)

> **Nothing you recorded is lost, and nothing is rewritten.** Memory layers, the
> decision ledger and the journal are the same JSON files in the same places.
> The upgrade adds; it does not migrate your knowledge out from under you.
>
> This is asserted, not asserted-to-be: `tests/demo/test_v1_upgrade.py` builds a
> real `10.0.0` install — six fact layers with no v2 fields, eight-field ADRs, a
> `RUN-#nnnn` audit trail, a config with no `settings` key — runs the upgrade,
> and checks every field of every record still says what it said.

---

## 1. Upgrade

```bash
git pull
coresentinel migrate      # creates the record store; touches no memory file
coresentinel doctor       # 10 subsystems
```

That is the whole procedure. `migrate` is idempotent — running it twice is a
no-op — and it does not move anything out of JSON.

---

## 2. The one thing that will surprise you

**If you recorded decisions before binding your first project, they are at Core
scope and a bound project will not show them by default.**

```console
$ cd ~/code/billing            # a bound project
$ coresentinel decision list
  0 decisions

$ coresentinel decision list --core
  ADR-001  File-based JSON layered memory
  ADR-002  Charge idempotency keys are mandatory
```

Nothing was deleted — `memory/decisions.json` is byte-for-byte what it was. A
bound project reads its own ledger **alone**, and that is deliberate: unioning
the scopes surfaced one repository's decisions as governance for another, and
the noise trained people to skip the check entirely. A guard nobody reads is
worse than no guard.

**What to do about it**, in order of preference:

1. Leave them at Core scope and read them with `--core`. Correct if they are
   genuinely cross-project decisions, which most v1 ADRs are.
2. Re-record the ones that belong to a specific repository inside it:
   `cd <project> && coresentinel decision add --title "..." --reason "..." --chosen "..."`.
   Ids are allocated across both scopes, so nothing collides.

`decision verify` follows the same scoping. Run it at Core scope for Core
decisions.

---

## 3. Your scores will drop, and that is the fix

`v1` awarded points for checks that never ran. An **empty directory** scored
`80/100 VERIFIED` on the claim *"I fixed the authentication vulnerability"*.

| | v1 | v2 |
| :--- | :--- | :--- |
| `verify` on an empty project | `VERIFIED 80/100` | `INDETERMINATE`, exit 2 |
| `score` on an empty project | `89/100` | `0/100 CRITICAL` |
| Linter, dependency audit, diff | hardcoded `PASS` | executed, or `UNKNOWN` |
| Health dimensions | 5 of 7 were constants | every one cites a command |

A project that read `100/100` may now read `62/100`. **The number did not get
worse; it started being measured.** Run `coresentinel score --explain` — every
point names the command behind it.

There is no `--legacy-scoring`. Keeping a fabricating code path alive behind a
flag reintroduces exactly what v2 removed, and it would be used in CI to
preserve a green number.

---

## 4. New exit code

`2` means **INDETERMINATE** — a check could not run, so the question was not
answered. It is not a softer `1`.

```bash
coresentinel verify --claim "..."
case $? in
  0) echo "verified" ;;
  1) echo "failed" ;;
  2) echo "could not be evidenced — no test runner, no git, nothing to check" ;;
esac
```

If your pipeline does `if [ $? -ne 0 ]`, an unbuildable project now fails it.
That is usually what you want; decide deliberately.

---

## 5. What is additive and needs nothing from you

| Area | Change |
| :--- | :--- |
| Memory layers | Unchanged on disk. New fields (`pinned`, `transferable`, `base_confidence`) are optional and absent means v1 |
| ADR schema | 8 fields → 20. `coresentinel migrate decisions` backfills the new ones as **null**, never inventing a value |
| Audit trail | v1 `RUN-#nnnn` records are kept and listed as `unverified_legacy`. They are **not** retro-signed — hashing them now would assert an integrity that never existed |
| Project config | A config with no `settings` key still binds. Settings are additive under that key |
| Commands | All 21 v1 commands, aliases and exit codes behave as documented. 11 new verbs are additive |
| `--json` | Every v1 key retained. `coresentinel_api` moves to `1.1` |
| Record store | New `coresentinel.db` / `records/`. **Deleting it loses no memory, decision or journal entry** — a test asserts the schema contains no table for them |

---

## 6. Configuration replaces `memorycore.conf`

`memorycore.conf` was written by both installers and read by no engine — dead
config carrying another machine's absolute paths. It is gone.

```bash
coresentinel config list              # every setting and where it came from
coresentinel config get storage.backend
coresentinel config set storage.backend sqlite --scope core
```

Precedence, lowest to highest: `default < core config < project config <
environment < flag`. Every value reports which layer produced it.

---

## 7. If something looks wrong

```bash
coresentinel doctor --verbose     # which of the 10 subsystems, and the remedy
coresentinel audit verify         # is the trail intact
coresentinel metrics budgets      # published performance limits
coresentinel config list          # what is actually configured, and from where
```

Memory is snapshotted before any destructive lifecycle operation, and every one
is a dry run until `--apply`:

```bash
coresentinel memory snapshots
coresentinel memory restore <id>
```

---

## 8. Rolling back

v2 writes no v1 file in a v2-only format, so downgrading is a `git checkout` of
the previous tag. The new record store and `coresentinel.config.json` are
ignored by v1. The one thing that does not come back is any decision you
re-recorded at project scope — those live in the project's ledger, which v1 does
not read.
