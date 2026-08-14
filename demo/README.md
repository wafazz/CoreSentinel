# taskflow — the reference project

A deliberately small Python project: a task store, its own passing pytest suite,
and nothing else. It exists so CoreSentinel can be shown governing **real code**
rather than a fixture built to agree with it.

`tests/demo/test_end_to_end.py` copies this directory, initialises a git
repository in the copy, and drives the whole chain against it. That test is the
only place in the suite that answers *"does the product work"* — everything else
tests a subsystem in isolation.

---

## What the chain proves

| Step | What is asserted |
| :--- | :--- |
| `init` | The project binds; the detected stack is seeded into **project** memory, not the shared Core |
| `doctor` | All 10 subsystems report on a real project, none FAIL |
| `project inspect` | Python and pytest are detected, and every finding names the file that proves it |
| `memory add` · `recall` | A recorded fact is findable again, and lands in the project's store — not the Core's |
| `decision add` | The ADR is written to the project ledger |
| **`decision verify`** | A change to "replace the in-memory dict with a postgres table" is **refused, exits 1, and cites the ADR plus the reason recorded at the time** |
| `context --task` | The pack stays inside its token budget and retrieves the decision relevant to the task |
| `task run` | The role pipeline runs with permissions enforced; a read-only agent is granted read-only |
| *(edit a file)* | A real change to `store.py`, with a real test added beside it |
| `review` | The static pass sees the change that was actually made |
| **`verify`** | **Testing evidence comes from executing taskflow's own pytest suite** — the number is somebody else's test run, not a fixture |
| `gate run` | Gates resolve from real evidence, each with a machine-readable reason code, none passing without a basis |
| `audit verify` | The hash chain is intact after the entire run |
| `metrics` | The run measured itself, and no performance budget was exceeded |
| `incident` · `pattern` | The learning ledgers record `INC-` and `PAT-` ids |

---

## Running it

```bash
# the whole chain, as CI runs it
python -m pytest tests/demo -q

# taskflow's own suite, on its own
cd demo && PYTHONPATH=. python -m pytest tests -q
```

The chain runs against a **sandbox copy of the Core**, never the repository.
`gate run` and Core-scoped writes go to the Core's own `memory/`, and a
subprocess cannot be monkeypatched — copying is the only isolation that holds. A
test asserts the checked-in `demo/` is never itself bound.

---

## The decision this project carries

`taskflow` keeps tasks in a plain dict. That is recorded as an ADR, with the
reason *"the demo must run with zero external services"*. The chain then tries to
reverse it, so you can watch the contradiction guard fire against a decision a
human actually made:

```console
$ coresentinel decision verify --change "replace the in-memory dict with a postgres table"

  Verdict   : REVIEW REQUIRED
  This change reverses a recorded decision.
  ...
$ echo $?
1
```

That exit code is the feature. A guard that does not change the exit code is
advice, and advice does not stop a pipeline.
