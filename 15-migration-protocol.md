# Database & Schema Migration Protocol (`Iris migrate`)

## Trigger
Activate when planning or executing database schema alterations, data backfills, or table restructuring. Command: `Iris migrate`.

## 1. Idempotency & Compatibility Rules
- **Idempotent SQL Guards**: Use `information_schema` + `PREPARE` statement wrappers for MySQL/MariaDB `ALTER TABLE` operations to safely execute repeatedly without error.
- **Cross-Version SQL**: Avoid version-restricted syntax (e.g. MySQL 8.4 syntax absent in MariaDB 10.4). Use explicit timestamp defaults (`DEFAULT CURRENT_TIMESTAMP`).
- **Delimiter Rules**: Remember `DELIMITER` commands cannot run under `PDO::exec()`; split multi-statement migrations cleanly.

## 2. Multi-Tenant Data Safety
- **Mandatory Tenant Scoping**: Every new multi-tenant table MUST include `tenant_id INT NOT NULL` and a composite index starting with `tenant_id` (e.g. `KEY idx_tenant_status (tenant_id, status)`).
- **Default Value Integrity**: Never add `NOT NULL` columns without a `DEFAULT` value on populated tables to prevent migration lockups.

## 3. Zero-Downtime & Lock Avoidance
- **Metadata Lock Protection**: Never run blocking `ALTER TABLE` queries on heavily-accessed live tables during high-traffic windows.
- **Safe Column Additions**: Add new columns as `NULLable` first, backfill data in batches, then apply constraints in a second migration step if needed.
- **Pre-Flight Test**: Test migrations against both full local test database and clean bootstrap schema.
