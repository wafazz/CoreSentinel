# MIMIC - Stack Migration Protocol
> "Same heart, different armor"

Migrate any project from one tech stack to another while preserving all business logic, structure, and behavior.

## When to Use
- {USER_NAME} says **"mimic this"** or asks to migrate/convert a project
- Rebuilding an existing app in a new framework
- Porting features from one tech stack to another

---

## Phase 1: Conversation (Iris Asks)
Gather all migration context before doing anything.

1. **Auto-detect current stack** — scan project files to identify framework, language, DB, frontend, packages
2. **Confirm with {USER_NAME}** — "Is this correct?" (show detected stack summary)
3. **Ask what to change** — full rewrite? backend only? frontend only?
4. **Ask target stack** — framework, language, DB, frontend
5. **Confirm migration plan** — summarize source → target and get approval

**Exit condition:** {USER_NAME} confirms the migration plan.

---

## Phase 2: Deep Scan
Map the entire source project structure.

**Captures:**
- Routes, Controllers, Models, Migrations
- Components, Services, Middleware
- API Contracts, Configs, Third-Party Integrations

**Output:** System Map — a complete inventory of the source project.

---

## Phase 3: Library Equivalence Mapping
Map every source library/tool to its target equivalent.

| Source | → | Target |
|--------|---|--------|
| ORM A | → | ORM B |
| Auth A | → | Auth B |
| Router A | → | Router B |

**Rules:**
- Present full mapping table to {USER_NAME}
- {USER_NAME} can approve or swap any mapping
- Only proceed after full approval

---

## Phase 4: Translation Plan Generation
Generate `project-plan.md` in the target project root.

**Structure:**
```
# Migration Plan: [Source] → [Target]

## Phase 1: Database & Setup
- [ ] Set up target project scaffold
- [ ] Migrate database schema
- [ ] Seed data

## Phase 2: Backend Core
- [ ] Models / Entities
- [ ] Routes / Endpoints
- [ ] Controllers / Handlers

## Phase 3: Backend Logic & Services
- [ ] Business logic services
- [ ] Middleware
- [ ] Authentication & Authorization

## Phase 4: Frontend Components
- [ ] Layouts & Pages
- [ ] Reusable components
- [ ] State management
- [ ] Routing

## Phase 5: Integrations
- [ ] Third-party services
- [ ] API contracts verification
- [ ] Environment config

## Phase 6: Testing & Verification
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual smoke test checklist
```

---

## Phase 5: Execute
Execute the plan systematically.

**Rules:**
- Read `project-plan.md` as the single source of truth
- Execute one todo at a time
- Save after each completed todo
- Mark completed items with `[x]`
- Never skip ahead — sequential execution only
- If blocked, flag to {USER_NAME} before moving on

---

## Migration History

| Date | Source Stack | Target Stack | Project | Status |
|------|------------|-------------|---------|--------|
<!-- Entries added after completed migrations -->
