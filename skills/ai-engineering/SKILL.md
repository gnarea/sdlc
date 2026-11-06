---
name: ai-engineering
description: How to build software on LLMs, whether directly on a model's API or around a harness such as a coding agent. Guidance and guardrails, determinism, evals, and portability, then prompts, context, harnesses, and model families. Use when writing, changing, or reviewing a prompt, an agent, a skill, the context that a model is given, or the harness that runs it.
---
# AI engineering

AI engineering comes down to _guidance_, the context that helps a model do its job well, and _guardrails_, which make it impossible for the model to cause damage, and easy for it to do whatever is common or reasonable.

A _harness_ is the software that runs a model: it gives the model its prompts and context, runs the tools that the model calls, and enforces what the model may do (e.g., Claude Code, an application built on a model's API). An _outer harness_ runs another harness instead of calling the model itself (e.g., a CI workflow or a terminal multiplexer that runs Claude Code), so it can only influence the model through what the inner harness exposes, such as its prompts, settings, and hooks.

Guardrails MUST be enforced by the harness (e.g., with a permission, a sandbox, an identity with limited privileges), and MUST NOT depend on an instruction or on another model's judgement alone (e.g., a classifier that approves actions), since a model can ignore or misread any instruction, and a classifier can be misled.

Some techniques need control over each call to the model (e.g., choosing which tools a call offers, pruning the history), so they're only available where the harness calls the model itself. The guidelines that rely on them say so. Where the harness doesn't offer such a technique, its goal MUST be met by other means, or the shortfall MUST be stated.

## Determinism

- Everything that can be deterministic MUST be deterministic: whatever code can compute, check, or enforce (e.g., formatting, validation, the order of steps, a permission) MUST be left to code, and the model MUST only be asked for what needs judgement.
- Every convention that a prompt asks the model to follow SHOULD also be enforced by a deterministic check where one exists (e.g., a spellchecker, a linter, a schema validator), run before the model's work can reach anyone else (e.g., before each commit, and again in CI), since the model will miss some slips, and so will a person reviewing its output.

## Evals

- Every change MUST be compared with what it replaces in evals, and new guidance also with having none, before it's adopted, with several independent runs of each, every one from a clean environment.
- The runs MUST use the model and harness that will run the prompt, at the lowest effort level that it'll run at, as well as at the default.
- The test cases MUST include prompts that only imply the task (e.g., "Is this OK to merge?"), prompts that state it (e.g., "Review this change"), and prompts for which the behaviour mustn't occur.
- Where the model chooses a skill or an agent by its description, whether it's chosen MUST be checked separately from whether it helps.
- Whatever a rule can decide (e.g., whether a skill was loaded, whether the tests pass) MUST be checked by code, and a model MAY only grade what needs judgement.
- Each guardrail MUST be tested by attempting what it forbids, and checking that the attempt failed, whilst the task that it allows still succeeds.
- Where the model doesn't do as instructed, its reasoning (e.g., a summary of its thinking) SHOULD be read to find out why, before the prompt is changed again.
- Of the changes that pass, the smallest SHOULD be adopted. A change that raises the cost (e.g., in tokens or time) without raising the success rate MUST be treated as a regression.
- The results MUST be reported as counts (e.g., 6/8 runs), along with the method and the exact version of each model and harness. A difference that the number of runs can't tell apart from chance SHOULD NOT be acted on.
- A defect in the model's output SHOULD be reported with real examples and measurements (e.g., the length of the documents that it wrote), and its fix MUST be run through evals with the same examples.

## Portability

A prompt is _portable_ where it must work with more than one model or harness (e.g., a plugin that others install in the harness of their choosing).

- Whether a prompt must be portable, and with which models and harnesses, MUST be decided before it's written, as it depends on who will run it.
- A portable prompt MUST NOT depend on anything specific to one model or harness, such as a development process, a tool, or a harness's syntax for invoking a skill (e.g., it refers to the `escalation` skill, rather than to `/sdlc:escalation` as in Claude Code).
- A portable skill MUST conform to the [Agent Skills specification](https://agentskills.io/specification).
- The evals of a portable prompt MUST cover each model and harness that it must work with.

## Additional guidelines

### By layer

- [Prompt engineering](references/prompt-engineering.md): The change writes or alters what a model is told: a system prompt (e.g., an agent's definition), a user prompt or its template, or a skill.
- [Context engineering](references/context-engineering.md): The change decides what a model is given, when, or from where (e.g., what to front-load, what to load on demand, what to delegate to another agent).
- [Harness engineering](references/harness-engineering.md): The change decides what a model can do or reach (e.g., its tools, permissions, or sandbox), or how the harness runs it.

### By model family

- [Anthropic Claude](references/anthropic-claude.md): A Claude model will run the prompt (e.g., Fable, Opus, Sonnet, or Haiku).
