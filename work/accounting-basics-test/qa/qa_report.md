# QA Report — accounting-basics-test

## Verdict
- approved: **false**
- score: **0/100**

## Blockers
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/9/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/10/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/11/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/12/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/13/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/14/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/15/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/indicators/16/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'high' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/0/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'high' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/1/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'high' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/2/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'high' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/3/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'medium' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/4/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** 'medium' is not one of ['critical', 'warning', 'info', 'low']
  - Evidence: `/structure/rules/5/severity`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/stages/17/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/stages/18/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/stages/19/description`
  - Fix: Fix Agent C output or schema mismatch.
- **[BLOCKER][schema]** '' should be non-empty
  - Evidence: `/structure/stages/20/description`
  - Fix: Fix Agent C output or schema mismatch.

## Next actions (pipeline)
1. Fix BLOCKER/MAJOR issues in Agent B output or Agent C compilation.
2. Re-run Agent C (compile) to regenerate `data/` and `docs/`.
3. Re-run Agent D (QA) until approved.
