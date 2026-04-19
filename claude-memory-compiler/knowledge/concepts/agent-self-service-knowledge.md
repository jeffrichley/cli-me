---
title: Agent Self-Service Knowledge
tags: [process, architecture, agent-patterns]
sources: [daily/2026-04-18.md]
created: 2026-04-18
updated: 2026-04-18
---

# Agent Self-Service Knowledge

Wiki reference pages must cover acquisition flows, not just enumeration. An agent that can list installed models but cannot find and install missing ones will stall on any task requiring an uninstalled dependency.

## The ComfyUI Case

The ComfyUI skill's initial wiki documented how to list installed models and checkpoints via the REST API. When an agent attempted a Flux generation workflow, it could see that no Flux model was installed but had no guidance on where to download one, which directory to place it in, or how to verify the download. The agent stalled.

Two new technique pages were required: `model-acquisition.md` (where to find models, how to download, which directory each type belongs in) and `flow-acquisition.md` (where to find workflows, format differences, how to convert). Together these closed the self-service gap.

## The Pattern

Enumeration-only documentation creates a class of tasks the agent cannot complete autonomously:

| Capability | Enumeration Only | With Acquisition |
|-----------|-----------------|-----------------|
| Use installed resource | Yes | Yes |
| Discover missing resource | Yes (can detect absence) | Yes |
| Obtain missing resource | **No — stalls** | Yes |
| Verify obtained resource | No | Yes |

## The Rule

For any skill that wraps a tool with external dependencies (models, plugins, extensions, datasets), the wiki must document:

1. **Enumeration** — how to list what's installed
2. **Acquisition** — where to find, how to download, where to place
3. **Verification** — how to confirm the resource is correctly installed
4. **Placement rules** — which directory/format each resource type requires (e.g., ComfyUI's `checkpoints/` vs `diffusion_models/` distinction)

## Broader Application

This extends beyond model files. Any agent-operated system with pluggable resources needs acquisition documentation: npm packages, Python dependencies, browser extensions, API keys, configuration files. The agent must be able to go from "I need X" to "X is ready" without human intervention.

See also: [[concepts/thin-wrapper-architecture]], [[concepts/two-tier-knowledge-routing]].
