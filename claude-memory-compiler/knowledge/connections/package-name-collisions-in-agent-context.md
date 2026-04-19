---
title: Package Name Collisions in Agent Context
tags: [process, tooling, agent-patterns]
sources: [daily/2026-04-18.md]
created: 2026-04-18
updated: 2026-04-18
---

# Package Name Collisions in Agent Context

When a package name on a registry (PyPI, npm) collides with a well-known project that distributes through other channels, agents will install the wrong package. This is especially dangerous because the install succeeds — the agent gets no error signal that it installed the wrong thing.

## The Nunchaku Case

PyPI's `nunchaku` package is an unrelated Gibbs sampler library. The actual SVDQuant/ComfyUI-nunchaku library (used for 4-bit quantized diffusion model inference) is distributed as pre-built wheels on GitHub, keyed to exact CUDA and PyTorch version combinations. An agent running `pip install nunchaku` gets a working install of the wrong library entirely.

## The Pattern

This is a specific instance of [[connections/interactive-prompts-in-agent-context|agent execution environment mismatches]]: agents operate with less context than human developers. A human would notice the PyPI description doesn't match, or would already know from community knowledge that this package isn't on PyPI. An agent sees a name match and proceeds.

The failure mode is silent: the package installs, imports may even succeed (different API surface), and the error only surfaces later as mysterious runtime failures.

## Defensive Measures

During the research phase of a skill build:

1. **Verify distribution channel.** Check the project's official documentation for how it's distributed. Don't assume PyPI/npm.
2. **Compare descriptions.** If the registry package description doesn't match the project's stated purpose, it's a collision.
3. **Check version alignment.** If the registry package's version history doesn't align with the project's release history, it's likely a different project.
4. **Document the install method.** When a tool requires non-standard installation (GitHub wheels, manual builds, conda-only), document this prominently in the wiki to prevent agents from defaulting to `pip install`.

## Broader Implication

This is another case where [[concepts/version-divergence|version divergence]] thinking applies: the name an agent finds may not correspond to the project it expects, just as the installed version may not match the source repository. Always verify identity, not just existence.

See also: [[concepts/version-divergence]], [[connections/interactive-prompts-in-agent-context]].
