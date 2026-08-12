# Git Workflow
> Consistent version control across all projects.

---

## Branch Strategy

```
main
├── feature/payment-gateway
├── fix/checkout-bug
├── hotfix/production-500
└── chore/update-dependencies
```

| Prefix | Use For | Example |
|---|---|---|
| `feature/` | New functionality | `feature/user-dashboard` |
| `fix/` | Bug fixes | `fix/login-redirect` |
| `hotfix/` | Urgent production fix | `hotfix/payment-callback` |
| `chore/` | Dependencies, config | `chore/update-packages` |
| `refactor/` | Code restructure | `refactor/extract-service` |

### Rules
- `main` is always deployable
- One feature per branch
- Delete branches after merge

---

## Commit Conventions

### Format
```
type: short description (max 72 chars)

Optional body explaining WHY, not WHAT.
```

### Types
| Type | Use For |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change (no new feature/fix) |
| `style` | UI/CSS only |
| `chore` | Config, deps, maintenance |
| `docs` | Documentation |
| `perf` | Performance improvement |
| `test` | Tests |

### Rules
- Present tense: "add feature" not "added feature"
- Lowercase after type
- Body explains WHY (the diff shows WHAT)

---

## When to Commit

| Situation | Commit? |
|---|---|
| Feature complete and tested | Yes |
| Milestone within large feature | Yes (checkpoint) |
| End of session (WIP) | Yes to feature branch |
| Quick fix (1-2 files) | Yes |
| Experimental (might revert) | To feature branch only |

### Agent Rule
- **Never commit unless {USER_NAME} explicitly asks**
- Stage specific files (not `git add .`)
- Never commit `.env` or secrets

---

## .gitignore Essentials

```gitignore
# Environment
.env
.env.local

# Dependencies
/vendor/
/node_modules/

# Build
/public/build/
/dist/

# IDE
.idea/
.vscode/
.DS_Store

# Logs
*.log
storage/logs/*

# Cache
bootstrap/cache/*
```

---

## Tag / Release

| Change | Bump | Example |
|---|---|---|
| Breaking change | Major | v1.0.0 → v2.0.0 |
| New feature | Minor | v1.0.0 → v1.1.0 |
| Bug fix | Patch | v1.0.0 → v1.0.1 |

```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

---

## Recovery

| Situation | Command |
|---|---|
| Undo last commit (keep changes) | `git reset --soft HEAD~1` |
| Discard local changes | `git checkout .` |
| Recover deleted file | `git checkout HEAD -- path/to/file` |
| Stash work temporarily | `git stash` → `git stash pop` |
