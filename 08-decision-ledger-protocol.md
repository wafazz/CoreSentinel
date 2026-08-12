# Architecture Decision Record (ADR) Ledger Protocol

> **Persistent Decision Tracking for AI Coding Squads**  
> Records architectural trade-offs, rationale, alternatives considered, and impact to eliminate repeated AI decision loops.

---

## 📜 Decision Record Schema

Every architectural decision is recorded in `memory/decisions.json`:

```json
{
  "id": "ADR-142",
  "decision": "Use PostgreSQL instead of MongoDB",
  "reason": "Transactional consistency required for payment ledger",
  "alternatives": ["MongoDB", "MySQL"],
  "chosen": "PostgreSQL",
  "impact": "High",
  "status": "Accepted",
  "created_at": "2026-08-12 11:25:00"
}
```

---

## ⚡ CLI Commands

```bash
# List all recorded architecture decisions
coresentinel decision list

# Query decisions for a specific keyword or technology
coresentinel decision list --query PostgreSQL

# Record a new architecture decision
coresentinel decision add \
  --title "Use PostgreSQL instead of MongoDB" \
  --reason "Transactional consistency required for payment ledger" \
  --chosen "PostgreSQL" \
  --alts "MongoDB, MySQL"
```
