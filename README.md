# Software Development Lifecycle (SDLC) plugin

The software development lifecycle, expressed as agents that carry a role's priorities and skills that carry its conventions.

The agents and skills are building blocks: the prompt or harness that uses them decides who each escalation goes to, and provides any process or tooling that they rely on.

_Endgame:_ to offload as much as I can to the LLM, so I can operate a "dark software factory" where I play the roles of Product Manager, Program Manager, Project Manager, and ultimate Systems Architect.

Install it from [my marketplace](https://github.com/gnarea/clone):

```
/plugin marketplace add gnarea/clone
/plugin install sdlc@gnarea
```

## Agents

- `architect`: Systems Architect, owning everything outside the OS process: inter-process contracts, backing services, and the deployment topology.
- `programmer`: Programmer and Software Architect, owning the codebase, its data model, and its security and privacy guarantees.
- `prototyper`: Prototyper, de-risking projects by planning, building, and testing throwaway prototypes in new and existing codebases.

## Skills

- `programming`: How to write and review code in any language.
- `systems-architecture`: How to design and review anything beyond the boundary of the OS process.
- `prototyping`: How to plan, build, test, and report on a throwaway prototype that de-risks a project.
- `project-management`: How to respond to a project's risks, whether threats or opportunities.
- `protocol-design`: How to design and review protocols and their specifications, on top of `systems-architecture`.
- `escalation`: When and how every agent escalates a hazard, and the hazards common to all of them.
- `artefact-review`: How to review an artefact that you didn't produce, such as a spec, a design, or a change, and how to process feedback on an artefact that you produced.
- `issue-tracking`: Templates and rules for creating, updating, and closing issues in any tracker, including the sign-off required before writing to one.
