# Debug Protocol
> "Don't go in circles. Isolate, diagnose, fix."

Activates when code breaks, tests fail, or Iris gets stuck.

---

## Rule #1: Three Strikes

If the same fix has been attempted 3 times and still fails:
- **STOP coding immediately**
- Re-read the error from scratch (not your assumption of it)
- Check if you're solving the right problem
- Consider a completely different approach
- If still stuck, ask {USER_NAME} for direction

---

## Step 1: Classify the Error

| Type | Symptoms | Example |
|---|---|---|
| **Build** | Won't compile/bundle | Module not found, npm/composer errors |
| **Runtime** | Crashes during execution | 500 error, undefined method, TypeError |
| **Logic** | Runs but wrong result | Wrong calculation, missing data, wrong status |
| **Integration** | External service fails | API 401/403, CORS, webhook not firing |
| **UI/Display** | Looks wrong | Layout broken, CSS missing, not rendering |
| **Data** | DB-related | Migration failed, constraint violation |

---

## Step 2: Isolate

### Build Errors
1. Read the FULL error message (not just the first line)
2. Check the exact file and line number
3. Verify package versions
4. Check for typos in imports
5. Clear caches, delete lock files, reinstall

### Runtime Errors
1. Check logs (server log, browser console)
2. Add debug output at the entry point — does it reach there?
3. Binary search: comment out half the code, narrow down
4. Check if error is in YOUR code or a package

### Logic Errors
1. Verify input data first
2. Trace the data flow step by step
3. Check the database directly
4. Compare with a working similar feature

### Integration Errors
1. Check credentials and mode (sandbox vs production)
2. Test the API call independently (curl/Postman)
3. Check request format matches docs
4. Check callback URL is accessible
5. Check provider's dashboard for logs

### UI/Display Errors
1. Browser DevTools → Console for JS errors
2. Inspect element → check CSS classes applied
3. Check component receives all required data
4. Hard refresh to clear browser cache

### Data Errors
1. Check migration ran successfully
2. Check column types match expectations
3. Check foreign key constraints
4. Check query scoping (multi-tenant data leak?)

---

## Step 3: Escalation Path

If isolate + fix doesn't work:

1. **Search the error** — exact message in docs/GitHub issues
2. **Check package version** — known bug? Try upgrading
3. **Simplify** — strip to minimum and test
4. **Compare** — find working example in Pattern Library or past project
5. **Ask {USER_NAME}** — explain what was tried, suggest 2 options

---

## Debug Log Template

When debugging a tough issue, log in session-memory:

```markdown
### Debug: [Short description]
- **Error**: [Exact error message]
- **Type**: [Build/Runtime/Logic/Integration/UI/Data]
- **Tried**:
  1. [Attempt 1] → [Result]
  2. [Attempt 2] → [Result]
- **Root cause**: [What was actually wrong]
- **Fix**: [What resolved it]
- **Prevention**: [How to avoid in future]
```

If the fix reveals a new anti-pattern, add it to Self-Evolution.
