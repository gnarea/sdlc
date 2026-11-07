---
name: ai-engineering
description: How to build software on LLMs, whether directly on a model's API or around a harness such as a coding agent. Guidance, guardrails, and determinism, then prompts, context, harnesses, evals, and model families. Use when designing a workflow that relies on LLMs, or when writing, changing, or reviewing a prompt, an agent, a skill, the context that an agent is given, or the harness that runs it.
---
# AI engineering

AI engineering comes down to _guidance_, the context that helps an agent do its job well, and _guardrails_, which make it impossible for the agent to cause damage, and easy for it to do whatever is common or reasonable.

This skill uses the following terms:

- _Agent_: a session in which a model works on a task, from a single call (e.g., to classify an email) to a long run with tools (e.g., reviewing a change on another agent's behalf).
- _Prompt_: any text that instructs an agent, such as a system prompt, a user prompt, or a skill.
- _Harness_: the software that runs an agent, giving it its prompts and context, running the tools that it calls, and enforcing what it may do (e.g., Claude Code, an application built on a model's API).
- _Outer harness_: a harness that runs another one instead of calling the model itself (e.g., a program that runs Claude Code sessions as steps of a workflow, or one that adds guardrails of its own around Claude Code), so it can only influence the agent through what the inner harness exposes, such as its prompts and settings.

Guardrails MUST be enforced by the harness (e.g., with a permission, confinement, an identity with limited privileges), and MUST NOT depend on an instruction alone, or on the judgement of an agent that reads the same untrusted input (e.g., a classifier that approves actions), since an agent can ignore or misread any instruction, and one that reads the same input can be misled by it.

Every change SHOULD be compared in evals with what it replaces, and new guidance also with having none, before it's adopted, following the [evals guidelines](references/evals.md).

## Determinism

- Everything that can be deterministic MUST be deterministic: whatever code can compute, check, or enforce (e.g., formatting, validation, the order of steps, a permission) MUST be left to code, and an agent MUST only be asked for what code can't do (e.g., interpreting a request written in plain language, drafting a design, reviewing a change).
- Every convention that a prompt asks an agent to follow SHOULD also be enforced by a deterministic check where one exists (e.g., a spellchecker, a linter, a schema validator), run before the agent's work can reach anyone else (e.g., before each commit, and again in CI), since the agent will miss some slips, and so will a person reviewing its output.

## Additional guidelines

### By layer

Each layer builds on the one before it.

1. [Prompt engineering](references/prompt-engineering.md): The change writes or alters what an agent is told: a system prompt (e.g., an agent's definition), a user prompt, project instructions, or a skill.
2. [Context engineering](references/context-engineering.md): The change decides what an agent is given, when, or from where (e.g., which tools it's offered, what to delegate to another agent, what to keep outside its context).
3. [Harness engineering](references/harness-engineering.md): The change decides what an agent can do or reach (e.g., data, systems), or how the harness runs it.

### By model family

Where Fable, Opus, Sonnet, or Haiku will run the prompt, or Claude Code will run the agent, see the [Anthropic Claude](references/anthropic-claude.md) guidelines.
