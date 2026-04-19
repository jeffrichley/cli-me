# Knowledge Base Index

Read this FIRST. This is the master catalog of all process knowledge for building cli-me skills.

| Article | Summary | Sources | Updated |
|---------|---------|---------|---------|
| [[concepts/article-formats]] | Standard templates for concept, connection, playbook, and QA articles | AGENTS.md | 2026-04-16 |
| [[concepts/qa-before-implementation]] | QA must come before implementation; three-tier QA framework | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/assertion-depth]] | Four levels of verification plus synthetic fixture trap — "runs" is not "works" | daily/2026-04-15-seed.md, daily/2026-04-18.md | 2026-04-18 |
| [[concepts/parallel-agent-research]] | Parallel agents for research (10 agents, 35 pages, 5 min) and implementation | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/fresh-context-for-review]] | Reviewers must have zero context from the creator's session | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/adversarial-review-system]] | Objective/judgment split, 3-strike auto-fix, 5 specialized reviewers; R5 execution testing most valuable | daily/2026-04-15-seed.md, daily/2026-04-18.md | 2026-04-18 |
| [[concepts/thin-wrapper-architecture]] | CLI thin wrapper + logic layer in commands/ module; split by command group | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/deterministic-before-llm]] | Use scripts for mechanically checkable tasks; reserve LLMs for semantic issues | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/version-divergence]] | Installed version may differ from source repo; always verify with installed binary | daily/2026-04-15-seed.md | 2026-04-16 |
| [[connections/url-rot-and-research-agents]] | Research agents cite unverified URLs; deterministic tools catch them | daily/2026-04-15-seed.md | 2026-04-16 |
| [[connections/interactive-prompts-in-agent-context]] | Interactive prompts silently hang agents; suppress with flags (-y, --force-overwrites) | daily/2026-04-15-seed.md | 2026-04-16 |
| [[concepts/two-tier-knowledge-routing]] | Process knowledge (Tier 1) vs tool-specific knowledge (Tier 2); routing rules and validation | daily/2026-04-16.md | 2026-04-18 |
| [[concepts/bootstrap-problem]] | Self-referential systems face chicken-and-egg on first run; design for graceful cold-start | daily/2026-04-16.md | 2026-04-18 |
| [[connections/cost-reporting-in-subscription-contexts]] | Agent SDK reports costs even on subscriptions; informational, not billing | daily/2026-04-16.md | 2026-04-18 |
| [[concepts/synthetic-fixture-trap]] | Synthetic test fixtures (sine tones) produce vacuous assertions when tool returns empty results | daily/2026-04-18.md | 2026-04-18 |
| [[concepts/agent-self-service-knowledge]] | Wiki must cover acquisition flows, not just enumeration; agents need to obtain missing resources | daily/2026-04-18.md | 2026-04-18 |
| [[connections/package-name-collisions-in-agent-context]] | Registry name collisions silently install wrong package; agents get no error signal | daily/2026-04-18.md | 2026-04-18 |
| [[connections/cross-reviewer-consensus]] | Multiple independent reviewers flagging same issue = high confidence signal | daily/2026-04-18.md | 2026-04-18 |
| [[playbooks/skill-build-process]] | End-to-end skill build: research, architecture, QA-first implementation, review, ship | daily/2026-04-15-seed.md | 2026-04-16 |
