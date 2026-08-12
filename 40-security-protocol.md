# Security Protocol
> Proactive security checks to run during development. Prevents common vulnerabilities before they reach production.

## When to Run
- Before every commit involving auth, payment, or user data
- When adding new routes or API endpoints
- When handling file uploads or external input
- When integrating third-party services
- When secrets or credentials are involved
- Automatically as part of the Review Protocol

---

## 1. Secret & Credential Protection

### Never Commit Secrets
- [ ] No API keys, tokens, or passwords in code
- [ ] No secrets in git history (check with `git log -p | grep -i "secret\|password\|token\|api_key"`)
- [ ] `.env` and credential files in `.gitignore`
- [ ] No hardcoded database credentials
- [ ] No secrets in frontend/client-side code

### If a Secret is Exposed
1. **Rotate immediately** — generate a new key/token
2. **Revoke the old one** — don't just replace, invalidate
3. **Scrub git history** if committed (use `git filter-branch` or BFG Repo-Cleaner)
4. **Audit access logs** for unauthorized usage
5. **Update `.gitignore`** to prevent recurrence

### Environment Variables
- [ ] All secrets stored in `.env` (never in code)
- [ ] `.env.example` exists with placeholder values (no real secrets)
- [ ] Production secrets managed via hosting platform's env config
- [ ] Different secrets for dev/staging/production

---

## 2. Input Validation & Injection Prevention

### SQL Injection
- [ ] Use parameterized queries or ORM — never raw string concatenation
- [ ] Validate and sanitize all user input before database queries
- [ ] Use allowlists for column names in dynamic queries (never user input directly)

### XSS (Cross-Site Scripting)
- [ ] All user-generated content escaped before rendering
- [ ] Use framework's built-in escaping (Blade `{{ }}`, React JSX auto-escapes)
- [ ] No `innerHTML`, `dangerouslySetInnerHTML`, or `{!! !!}` with user data
- [ ] CSP (Content Security Policy) headers configured

### CSRF (Cross-Site Request Forgery)
- [ ] CSRF tokens on all state-changing forms
- [ ] Only exempt webhook/callback routes (document why)
- [ ] API routes use token-based auth instead of session cookies

### Command Injection
- [ ] No user input passed to shell commands (`exec`, `system`, `shell_exec`)
- [ ] If unavoidable, use allowlists and escape functions

---

## 3. Authentication & Authorization

### Authentication
- [ ] Passwords hashed with bcrypt/argon2 (never MD5/SHA1)
- [ ] Login rate limiting / brute force protection
- [ ] Session regeneration after login
- [ ] Secure session configuration (httpOnly, secure, sameSite)
- [ ] Password reset tokens are single-use and time-limited

### Authorization
- [ ] Every route has appropriate middleware (auth, role, permission)
- [ ] Server-side authorization check — never trust frontend-only checks
- [ ] Users can only access/modify their own resources (ownership check)
- [ ] Admin routes separated and protected
- [ ] API endpoints verify token scopes

---

## 4. Data Isolation (Multi-Tenant / Multi-User)

- [ ] All queries scoped by user/tenant/organization ID
- [ ] No cross-user data leakage in list/show/edit/delete
- [ ] Authorization checked before update/delete (user owns the resource)
- [ ] Search and filter queries also scoped
- [ ] File uploads stored in user-scoped directories
- [ ] Cached data keyed by user/tenant (no cache poisoning)

---

## 5. File Upload Security

- [ ] Validate file type (MIME type + extension, not just extension)
- [ ] Enforce maximum file size
- [ ] Rename uploaded files (never use original filename as-is)
- [ ] Store outside web root or use access-controlled storage
- [ ] Scan for malicious content if accepting documents
- [ ] Old files deleted on re-upload (no orphaned files)
- [ ] No directory traversal in file paths (`../`)

---

## 6. API Security

- [ ] Rate limiting on all public endpoints
- [ ] Authentication required for sensitive endpoints
- [ ] Input validation on all request parameters
- [ ] Response doesn't leak internal errors or stack traces
- [ ] CORS configured restrictively (not `*` in production)
- [ ] Pagination enforced (no unbounded queries)
- [ ] Sensitive data filtered from logs

---

## 7. Dependency Security

- [ ] No known vulnerable packages (run `npm audit` / `composer audit`)
- [ ] Lock files committed (`package-lock.json`, `composer.lock`)
- [ ] Dependencies from trusted sources only
- [ ] Unused dependencies removed
- [ ] Regular update schedule for security patches

---

## 8. Production Hardening

- [ ] Debug mode OFF in production
- [ ] Error pages don't expose stack traces or internal paths
- [ ] HTTPS enforced (redirect HTTP to HTTPS)
- [ ] Security headers set (X-Frame-Options, X-Content-Type-Options, HSTS)
- [ ] Database backups configured and tested
- [ ] Logging enabled for auth events and errors
- [ ] Admin panel not publicly accessible (IP restrict or VPN)

---

## Quick Security Scan (5-Second Check)
For any change, at minimum verify:
1. **Secrets safe?** — No keys/tokens in code or git
2. **Input trusted?** — All user input validated/escaped
3. **Access controlled?** — Auth + ownership checks on route
4. **Data scoped?** — Queries filtered by user/tenant

---

## Incident Response
If a vulnerability is discovered in production:
1. **Contain** — Disable affected feature or route
2. **Assess** — Determine scope and data exposure
3. **Fix** — Patch the vulnerability
4. **Rotate** — Change any compromised credentials
5. **Notify** — Inform affected users if data was exposed
6. **Log** — Document in Self-Evolution as anti-pattern
