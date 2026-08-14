# Init Protocol
> "Start from experience, not from zero."

Triggered when {USER_NAME} says **"Iris init"** or asks to start a new project.

---

## Phase 1: Gather Context

Ask {USER_NAME} (one message, not one by one):

1. **Project name** — What's the project called?
2. **Project type** — E-commerce, SaaS, booking, portfolio, management system, API, etc.
3. **Stack preference** — Or say "recommend" and Iris picks based on project type
4. **Key features** — What are the 3-5 main features?
5. **Multi-role?** — How many user roles? What are they?
6. **Payment?** — Which gateway? (or none)
7. **Deployment target** — VPS, Docker, shared hosting, Vercel, etc.

---

## Phase 1.5: Learn Mode Check

After gathering context, check if the chosen stack exists in `11-pattern-library.md`:
- **Stack found?** → Continue normally (full pattern support)
- **Stack NOT found?** → Activate **Learn Protocol** (`10-learn-protocol.md`). Run Research Sprint before proceeding.

---

## Phase 2: Stack Recommendation

If {USER_NAME} says "recommend", use past project experience to suggest a stack.
As you complete more projects, build your recommendation table here:

| Project Type | Recommended Stack | Why |
|---|---|---|
<!-- Add recommendations as you gain experience -->
<!-- Example: | E-commerce | Laravel + Inertia + React | Proven in Project X | -->
<!-- Example: | SaaS multi-tenant | Laravel + Filament + Stancl | Proven in Project Y | -->

---

## Phase 3: Generate Project Scaffold

### 3a. Create MemoryCore Profile
Create `Projects/NN-{project-slug}.md` in the Core directory using the `_template.md`.

### 3b. Register in Identity
Add entry to `00-identity.md` Active Projects list.

### 3c. Register Stats Label
Add entry to `~/.claude/project-labels.json` mapping the project's folder key to a clean display name.

### 3d. Create Session Memory
Create `session-memory.md` in project root using the template from `04-session-memory-format.md`.

### 3e. Create Planning Doc (if complex)
For projects with 3+ features, create `Planning.md` in project root:
- Database schema design
- Route plan
- Phase breakdown
- Key decisions

---

## Phase 4: Apply Patterns from Library

Based on the project's needs, pull proven patterns from `11-pattern-library.md`.
Document which patterns were applied in the project profile.

---

## Phase 5: Scaffold & Start

1. Run framework scaffold command
2. Install packages based on stack
3. Set up config/env
4. Create initial migrations
5. Create models with relationships
6. Set up auth
7. Create base layout
8. Seed demo data
9. Verify everything works

---

## Phase 6: Handoff

After scaffold is verified:
- Update session-memory.md with Phase 1 complete
- Update MemoryCore profile with completed items
- Continue to Phase 2 (feature development)
