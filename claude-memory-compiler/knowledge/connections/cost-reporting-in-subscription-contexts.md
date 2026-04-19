---
title: Cost Reporting in Subscription Contexts
tags: [tooling, agent-patterns]
sources: [daily/2026-04-16.md]
created: 2026-04-18
updated: 2026-04-18
---

# Cost Reporting in Subscription Contexts

Agent SDK tooling reports `total_cost_usd` even when the user is on a flat-rate subscription (e.g., Claude Max). The number represents what the usage *would* cost on API billing, not an actual charge. This is an informational metric, not a billing event.

## Why This Matters

Users will see cost figures and ask whether they're being charged. The answer depends on their billing model:

- **API billing:** The reported cost is real and will appear on their invoice.
- **Subscription (Claude Max, etc.):** The cost is informational only. Usage is covered by the subscription.

## The Broader Pattern

This is an instance of a general agent-tooling pitfall: **metrics designed for one context appearing in another**. The cost metric exists for API users who need to track spend. When the same tooling runs under a subscription, the metric persists but its meaning changes. The UI doesn't distinguish between the two contexts.

When building tools that surface metrics, consider whether the metric's meaning is context-dependent and whether the presentation makes the context clear.

See also: [[concepts/bootstrap-problem]], [[concepts/version-divergence]].
