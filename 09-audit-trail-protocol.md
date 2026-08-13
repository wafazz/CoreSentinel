# 🛡️ AI Accountability Audit Trail Protocol

> **Append-only, hash-chained, and covering twelve subjects rather than one.**
> An audit trail you can silently rewrite is worse than no trail, because it looks like one.

---

## 🔗 The Chain

Every record carries the hash of the record before it. That single link is what turns a list
into evidence: the chain detects the four ways a trail actually gets falsified.

| Falsification | How it shows up | Code |
| :--- | :--- | :--- |
| **Mutation** | A record's own hash no longer matches its content | `RECORD_MUTATED` |
| **Deletion** | The next record's `prev_hash` points at something that is gone | `CHAIN_BROKEN` |
| **Insertion** | Sequence numbers collide, and the link breaks either side | `SEQUENCE_BROKEN` |
| **Reordering** | `prev_hash` no longer matches the record that now precedes it | `CHAIN_BROKEN` |

```bash
coresentinel audit verify          # exits 1 if anything was altered
coresentinel audit verify --json
```

> **This is tamper-evidence, not tamper-proofing.** Anyone with write access can recompute the
> whole chain. What they cannot do is change one record and leave the rest intact — and that
> is what a quiet edit actually looks like.

---

## 📋 The Twelve Subjects

v1 recorded one of these. The other eleven happened with no trace: a memory fact could be
rewritten, a rule changed, a gate waived, and nothing anywhere said so.

| Subject | Recorded when |
| :--- | :--- |
| `agent_action` | An agent starts or completes a task |
| `memory_change` | A fact is recorded or updated |
| `decision` | An ADR is created or superseded |
| `rule_change` | An evolution proposal is raised or approved |
| `task_execution` | A pipeline run starts or finishes |
| `file_change` | An agent writes a file through the sandbox |
| `command_execution` | An agent runs a command through the sandbox |
| `quality_gate` | The gate pipeline is evaluated |
| `verification` | The evidence suite runs |
| `incident` | An incident is recorded |
| `deployment` | A deployment completes |
| `configuration_change` | A setting is changed, or a project is bound |

```bash
coresentinel audit coverage        # which subjects have ever been recorded here
```

A subject with no records has either never happened in this store, or nothing emits an event
for it. Both are worth knowing, and neither is hidden.

---

## 🔌 How Wiring Works

Auditing is wired through the **event bus**, not by calling the ledger from a dozen places.
That means *emitting an event is how something gets audited*: a subsystem added later either
emits and is recorded, or does not and shows up as an unrecorded subject in `audit coverage`.

A failure to write an audit record is logged loudly and never fails the operation being
audited. A governance tool that breaks the work because it could not describe the work is a
governance tool people switch off.

---

## 🔒 Redaction

Records are redacted **before they are written**, not before they are displayed, using the
same rules as the logger — one implementation, so the two cannot drift about what counts as a
secret. Field names that look sensitive lose their values entirely; credential shapes in free
text (`sk_live_…`, `ghp_…`, `AKIA…`, `Bearer …`, PEM blocks, credentials in a URL) are
substituted wherever they appear.

The redacted content is what gets hashed, so a redacted record still verifies.

---

## 🕰️ The Legacy Boundary

Records written before chaining existed are imported and listed as `unverified_legacy`. They
are **never retro-signed**: hashing them now would assert an integrity that never existed,
which is the opposite of what an audit trail is for.

Records written straight to the collection rather than through the ledger are counted and
reported separately. Bypassing the chain is visible, not silent.

---

## 🧾 Record Schema

```json
{
  "id": "AUD-000042",
  "seq": 42,
  "subject": "decision",
  "actor": "Iris",
  "action": "DecisionCreated",
  "result": "Accepted",
  "detail": { "decision": "ADR-042", "chosen": "Redis" },
  "recorded_at": "2026-08-14 11:34:49",
  "prev_hash": "sha256:9f0ab2c41d7736e8...",
  "hash": "sha256:1b375a38128d4e6a..."
}
```

---

## ⚡ CLI Commands

```bash
coresentinel audit list                    # chronological trail
coresentinel audit show AUD-000042         # one record
coresentinel audit verify                  # walk the chain, exit 1 on tampering
coresentinel audit coverage                # subjects recorded vs never recorded
coresentinel audit record --agent "..." --task "..."
```
