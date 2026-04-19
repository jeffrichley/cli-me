---
title: Cross-Reviewer Consensus as Confidence Signal
tags: [process, review, agent-patterns]
sources: [daily/2026-04-18.md]
created: 2026-04-18
updated: 2026-04-18
---

# Cross-Reviewer Consensus as Confidence Signal

When multiple independent reviewers — each with [[concepts/fresh-context-for-review|fresh context]] and different review specializations — flag the same issue, confidence that the issue is real approaches certainty. This transforms the adversarial review system from a list of individual findings into a prioritization tool.

## The Pyannote Case

During the pyannote adversarial review, three independent reviewers (R1: factual accuracy, R3: code-wiki alignment, R5: execution testing) all flagged the same embedding shape mismatch: code comments said `(1, 256)` but the actual API returns `(256,)`. Each reviewer discovered this independently through different methods — R1 by reading documentation, R3 by comparing code against wiki, R5 by running the actual API. The convergence confirmed it was a real issue worth fixing, not a style preference.

## The Analysis Method

After all reviewers complete, a cross-reviewer consensus analysis collects findings into categories:

1. **Unanimous or near-unanimous flags** — highest priority, definitely real
2. **Single-reviewer flags with evidence** — likely real, verify
3. **Single-reviewer flags without evidence** — may be judgment calls, accumulate for human decision

This is more valuable than treating all findings equally. A finding flagged by one reviewer might be a false positive or a style preference. A finding flagged by three reviewers using three different methods is almost certainly a defect.

## Relationship to the Adversarial Review System

Cross-reviewer consensus is an emergent property of the [[concepts/adversarial-review-system|adversarial review system]]'s design: because the five reviewers have non-overlapping specializations, their findings are largely independent. When findings do overlap, it's because the issue is visible from multiple angles — a strong signal.

This also validates the investment in running all five reviewers rather than a subset. Consensus can only emerge when there are enough independent perspectives to converge.

See also: [[concepts/adversarial-review-system]], [[concepts/fresh-context-for-review]].
