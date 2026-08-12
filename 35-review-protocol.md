# Review Protocol
> Self-review checklist before delivering code. Run after every significant task.

## When to Run
- After multi-file changes
- After new feature implementation
- After payment/auth/security-related changes
- After database schema changes
- Before saying "done" to {USER_NAME}

---

## Checklist

### 1. Variables & Types
- [ ] All variables initialized before use
- [ ] No undefined variable warnings
- [ ] Type definitions updated (if using TypeScript)

### 2. Security
- [ ] No SQL injection (use parameterized queries or ORM)
- [ ] No mass assignment vulnerability (use allowlists)
- [ ] CSRF exempted ONLY for payment/webhook callbacks
- [ ] File uploads validated (type, size)
- [ ] No sensitive data exposed to frontend (passwords, secrets, tokens)
- [ ] Auth middleware on all protected routes

### 3. Data Isolation (Multi-User / Multi-Tenant)
- [ ] Queries scoped by user/tenant/owner ID
- [ ] No cross-user data leaks in show/edit/delete routes
- [ ] Authorization check: user owns the resource before update/delete

### 4. File Uploads (if applicable)
- [ ] Using correct upload method for framework
- [ ] Old file deleted on re-upload
- [ ] Storage accessible (symlinks, permissions)
- [ ] Using relative paths (not hardcoded URLs)

### 5. Payment Integration (if applicable)
- [ ] Callback route CSRF-exempted
- [ ] Return route handles cross-site POST (session loss)
- [ ] Status only set to paid/active AFTER payment confirmation
- [ ] Transaction ID stored
- [ ] Duplicate payment prevention

### 6. Database
- [ ] Timestamp columns nullable (strict mode)
- [ ] No reserved table names (avoid framework conflicts)
- [ ] Foreign keys have proper `onDelete` behavior
- [ ] New columns have defaults or are nullable
- [ ] Migration is reversible

### 7. Frontend (if applicable)
- [ ] Forms work for both create AND edit
- [ ] Flash/toast messages display (success + error)
- [ ] Loading states on submit buttons
- [ ] Mobile responsive (no overflow, no hidden content)

### 8. Controller → View Data
- [ ] Controller passes ALL data the view/component uses
- [ ] No missing prop causing crash or blank page
- [ ] Pagination data included if using paginated queries

### 9. Routes
- [ ] New routes added to correct group
- [ ] Middleware applied (auth, role, subscription)
- [ ] Route names consistent with existing convention
- [ ] No duplicate route names or URIs

### 10. Edge Cases
- [ ] Empty state handled (no data yet)
- [ ] Deleted parent doesn't crash child queries
- [ ] Concurrent access handled (lock for update on stock/balance)
- [ ] Soft-deleted records excluded from active lists

---

## Quick Scan (3-Second Check)
For small changes, at minimum verify:
1. **Will it crash?** — Missing data, undefined vars, null references
2. **Is it safe?** — Auth check, data scoping, no injection
3. **Does it match?** — Existing code style, naming convention, UI pattern

---

## Stack-Specific Extras
<!-- Add your own stack-specific checks as you discover them -->
<!-- Example:
### Laravel + Blade
- [ ] @csrf in forms
- [ ] @method('PUT') for update forms
- [ ] old() values in form inputs

### React + Inertia
- [ ] router.post with _method for file upload updates
- [ ] preserveScroll on delete actions
- [ ] Error display from page props
-->
