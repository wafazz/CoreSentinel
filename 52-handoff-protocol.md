# Handoff Protocol
> "Ship it clean. Leave nothing unexplained."

Triggered when a project is done and ready for delivery.

---

## When to Use
- Project is feature-complete
- Client needs to take over
- Another developer will continue
- First production deployment
- Archiving a completed project

Manual trigger: **"Iris handoff"**

---

## Phase 1: Documentation

### README.md
Generate or update with:
- Tech stack summary
- Requirements
- Installation steps (clone, install, configure, migrate, build, run)
- Environment variables table
- Default accounts
- Scheduled commands (if any)
- Folder structure overview

### API Documentation (if applicable)
- All endpoints with method, URL, params, response
- Auth requirements
- Example requests

---

## Phase 2: Code Cleanup

- [ ] Remove all debug statements (dd, dump, console.log)
- [ ] Remove commented-out dead code
- [ ] Remove unused imports
- [ ] No hardcoded localhost URLs
- [ ] No test data in production seeders
- [ ] `.env.example` has ALL required keys (no values)
- [ ] `.gitignore` excludes sensitive files
- [ ] No broken routes
- [ ] Build passes without errors
- [ ] Storage permissions documented

### Security Check
- [ ] No API keys in code (all in .env)
- [ ] No plaintext passwords in seeders (production)
- [ ] CSRF active on all forms
- [ ] Auth middleware on protected routes
- [ ] Input validation on all forms
- [ ] File upload limits enforced

---

## Phase 3: Database

```bash
# Fresh migration test — proves it works from zero
php artisan migrate:fresh --seed   # or equivalent
```

- Document table list with purpose
- Document key relationships
- Note any important enum values

---

## Phase 4: Deployment

Pull the appropriate recipe from `51-deployment-protocol.md`.
Include server requirements and step-by-step commands.

### Post-Deploy Verification
- [ ] App loads
- [ ] Login works for all roles
- [ ] Core features work
- [ ] File uploads work
- [ ] Payment flow works (if applicable)
- [ ] Emails send (if applicable)

---

## Phase 5: Delivery Package

```
project/
├── Source code (git repo or zip)
├── README.md
├── .env.example
├── DEPLOYMENT.md (if VPS)
└── docs/ (if complex)
```

### Communicate to Client
1. Source code access
2. Credentials (via secure channel, NOT with code)
3. Server access details
4. Third-party account access
5. Known issues / planned features
6. Support period agreement

---

## Phase 6: Archive

After handoff:
1. Update project profile status to `Delivered`
2. Log delivery date
3. Note ongoing maintenance commitments
4. Update deployment memory with production details
