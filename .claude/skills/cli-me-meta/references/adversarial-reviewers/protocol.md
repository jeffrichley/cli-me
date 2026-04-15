# Adversarial Reviewer Prompts

These are the prompts used to dispatch fresh reviewer agents at each phase
of skill building. Each reviewer has ZERO context from the creator's session.
They see only the artifact and these instructions.

**Core principle:** The reviewer's job is to find problems, not confirm quality.
A review that finds nothing is suspicious — push harder.

---

## Review Result Handling Protocol

The coordinator (orchestrating agent) handles review results mechanically.
LLM judgment is unreliable for "good enough" decisions, so criteria are
objective wherever possible.

### Finding Categories

**Category 1: Objective Failures** — binary, no judgment needed:
- Command exits non-zero → auto-fix
- URL returns 404/5xx → auto-fix (remove or replace URL)
- Wiki says flag X, code uses flag Y → auto-fix
- Test assertion is shallow (e.g., `file.exists()` only) → auto-fix
- Output has wrong codec/dimensions/duration/format → auto-fix
- Missing required section in wiki page → auto-fix

**Category 2: Judgment Calls** — human decides:
- "This best practice claim seems outdated but I'm not sure"
- "Edge case handling is minimal but may be sufficient"
- "The creative hunt found a scenario that might be a problem"
- "A review that finds zero issues" (suspicious)

### Fix-Review Loop

```
Reviewer finds objective failure
  → Coordinator dispatches FIX AGENT (fresh, not the reviewer)
  → Fix agent makes the change
  → Coordinator re-dispatches SAME REVIEWER to verify the fix
  → Still failing? Loop again (max 3 cycles)
  → Still failing after 3? ESCALATE TO HUMAN with full evidence
```

### Rules

1. **3-strike limit on auto-fix.** Objective failure → fix → re-review.
   If the same finding persists after 3 fix-review cycles, STOP and
   escalate to human. This prevents infinite loops.

2. **Reviewer never fixes.** Reviewers report findings. Fix agents fix.
   Reviewers re-verify. Mixing roles creates echo chambers.

3. **Judgment calls accumulate.** Do NOT block on each one. Collect them
   and present a batch to the human at phase boundaries. Format:
   ```
   ## Judgment Calls for Human Review
   
   1. [REVIEWER 1, convert-video-format.md] "The -movflags +faststart
      recommendation may not apply to MKV output — uncertain."
      Evidence: [link to page, line reference]
      Risk: Low — MKV ignores the flag silently
      
   2. [REVIEWER 4, test_convert_format] "This test would still pass
      if the codec was wrong but the file existed."
      Evidence: [test code]
      Risk: Medium — false confidence in test suite
   ```

4. **Zero-findings flag.** If a reviewer finds NOTHING:
   - Note it in the review summary
   - Optionally re-dispatch with a more aggressive prompt:
     "The previous reviewer found zero issues. This is suspicious.
     Look harder. What did they miss?"
   - If the second reviewer also finds nothing, accept it

5. **Phase gate.** A phase CANNOT complete with unresolved objective
   failures. Judgment calls CAN be deferred to the next human checkpoint.
   The coordinator presents the summary and waits for go/no-go.

6. **Fix agent instructions.** When dispatching a fix agent, provide:
   - The exact finding (reviewer's report)
   - The file path and line numbers
   - What the correct behavior should be
   - Do NOT provide the reviewer's suggested fix — let the fix agent
     figure out the right solution independently

### Human Checkpoint Format

At each phase boundary, the coordinator presents:

```
## Phase [N] Review Summary

### Objective Failures: [N resolved / N total]
All resolved via auto-fix loop.
(Or: [N] escalated after 3 fix cycles — details below)

### Judgment Calls: [N items]
[numbered list with evidence and risk assessment]

### Reviewer Confidence
- Reviewer 1: Found [N] issues (suspicious: [yes/no])
- Reviewer 2: Found [N] issues

### Decision Needed
Proceed to Phase [N+1]? [yes/no]
```
