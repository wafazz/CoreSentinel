## Description
<!-- Provide a brief, clear summary of what this change does and the motivation behind it. -->

## Changes Made
- 

## Verification & Evidence
<!-- In accordance with "Nothing reports a result it did not measure", provide the actual command outputs / test runs. -->

- [ ] `python -m pytest tests -q` passed
- [ ] `python sentinel-validator.py` passed (no secrets / anti-patterns)
- [ ] `python coresentinel.py doctor` passed
- [ ] `python coresentinel.py review` passed

```text
<!-- Paste terminal verification output or test summary here -->
```

## Architectural Invariants
- [ ] No direct storage bypass from surfaces (`coresentinel_core/services/facade.py` used)
- [ ] Any new command/flag registered in `coresentinel.py` (and `VALUE_FLAGS` if applicable)
- [ ] No weakened or deleted test assertions
- [ ] Documented in matching `NN-protocol.md` if applicable
