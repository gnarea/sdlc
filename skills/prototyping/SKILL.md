---
name: prototyping
description: How to de-risk a project with a throwaway prototype. Use when planning, building, testing, or reporting on a prototype, or when reviewing one.
---
# Prototyping

A _prototype_ is software built to answer questions about a project, and thrown away once it has answered them, even where it's built in an existing codebase. It may be built to put something tangible in front of customers or users, to establish whether the project is feasible, or to show what building it for real would entail.

You MUST follow the guidelines for the task at hand:

- [Planning](references/planning.md) a prototype, using the [plan template](assets/plan.md).
- [Building](references/building.md) a prototype.
- [Testing](references/testing.md) a prototype.
- [Reporting](references/reporting.md) on a prototype, using the [report template](assets/report.md).

Unless you're asked to use a different template or format, you MUST use the task's template, leaving out any section that has nothing in it.

## Lifecycle

- The prototype MUST be planned before it's designed or built, and the plan MUST be updated whenever a result changes its questions or its compromises.
- The prototype MUST end with a report. Once the report is written, any infrastructure that the prototype provisioned MUST be removed, along with any data that it collected.
- The prototype MUST NOT be deployed to production.

## People taking part

- A compromise MUST NOT extend to people who aren't taking part: the prototype MUST NOT be able to overwhelm another system or be used against one, and MUST NOT collect their data or spend their devices' resources.
- A protection for those who do take part MAY be left out only where they're told before they use the prototype, and can decline.
