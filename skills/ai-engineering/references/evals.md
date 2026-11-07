# Evals

- Each eval MUST be run several times, independently and from a clean environment every time, on the model and harness that will run the prompt, at the lowest effort level that it'll run at, as well as at the default.
- The test cases MUST include prompts that only imply the task (e.g., "Is this OK to merge?"), prompts that state it (e.g., "Review this change"), and prompts for which the behaviour mustn't occur.
- Whatever a rule can decide (e.g., whether a skill was loaded, whether the tests pass) MUST be checked by code, and an agent MAY only grade what code can't.
- Each guardrail MUST be tested by attempting what it forbids, and checking that the attempt failed, whilst the task that it allows still succeeds.
- Where an agent doesn't do as instructed, its reasoning (e.g., a summary of its thinking) SHOULD be read to find out why, before the prompt is changed again.
- Of the changes that pass, the simplest SHOULD be adopted. A change that raises the cost (e.g., in tokens or time) without raising the success rate MUST be treated as a regression.
- The results MUST be reported as counts (e.g., 6/8 runs), along with the method and the exact version of each model and harness. A difference that the number of runs can't tell apart from chance SHOULD NOT be acted on.
- A defect in an agent's output SHOULD be reported with real examples and measurements (e.g., the length of the documents that it wrote), and its fix MUST be run through evals with the same examples.
