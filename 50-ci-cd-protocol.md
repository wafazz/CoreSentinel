# Continuous Integration & Pipeline Protocol (`Iris ci`)

## Trigger
Activate when building, configuring, or troubleshooting CI/CD workflows (GitHub Actions, GitLab CI, Jenkins). Command: `Iris ci`.

## 1. Environment & Config Isolation
- **Test Environment File**: Ensure `.env.test` is never silently ignored or mutated by production setup scripts.
- **Gitignore Negation**: If `.gitignore` contains `.env.*`, explicitly negate `.env.test` (`!.env.test`) or inject it via secrets during pipeline setup.

## 2. Dependency & Platform Floor Guards
- **Platform PHP Lock Match**: Ensure `composer.lock` dependencies match the exact PHP floor version declared in `composer.json` (e.g. PHP 8.2). Avoid platform requirement mismatches.
- **CI Dependency Command**: Run dependency installs with strict platform checks (`composer install --no-interaction --prefer-dist`).

## 3. Database & Migration Pipeline Tests
- **Clean Test Database**: Re-create and apply all SQL migrations cleanly from scratch before running feature/integration tests.
- **Shared Table Truncation**: Ensure every test suite cleans up shared multi-tenant tables in `setUp()` to prevent cross-test state leakage.
