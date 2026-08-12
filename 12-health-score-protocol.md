# 🛡️ CoreSentinel Health Score & Reliability Protocol

> **Quantified 7-Dimension Health Score & System Status Rating**  
> Evaluates project quality across Architecture, Security, Testing, Code Quality, Documentation, Reliability, and Dependencies.

---

## 📊 Health Dimensions Matrix

| Dimension | Max Points | Evaluation Basis |
| :--- | :--- | :--- |
| **Architecture** | 100 pts | Component design, Mermaid diagram & requirement spec completeness |
| **Security** | 100 pts | `sentinel-validator` zero secret leaks & OWASP AppSec rules |
| **Testing** | 100 pts | Unit/Integration test runner pass rate & test suite density |
| **Code Quality** | 100 pts | Linter clean, zero anti-patterns & zero superficial patches |
| **Documentation**| 100 pts | `README.md`, protocol coverage, & API documentation completeness |
| **Reliability** | 100 pts | Git repository stability & failure recovery |
| **Dependencies** | 100 pts | Valid lockfile presence & zero critical CVEs |

---

## 🚦 System Health Status Ratings

- **`HEALTHY` (Overall Score >= 90/100)**: Production-ready baseline. All quality standards met.
- **`WARNING` (Overall Score 75–89/100)**: Non-blocking issues present. Remediation recommended.
- **`CRITICAL` (Overall Score < 75/100)**: Gate failure. Deployment blocked until remediated.

---

## ⚡ CLI Commands

```bash
# Evaluate & print formatted CoreSentinel Health Scorecard
coresentinel score

# Alias command
coresentinel health

# Output machine-readable JSON health report for CI/CD pipelines
coresentinel score --json
```
