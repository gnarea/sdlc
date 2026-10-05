# (System)

(A paragraph for a technical reader who doesn't know the domain's vocabulary, followed by a diagram of the system and those who interact with it.)

## Purpose

(The problem, with no solution in it, followed by the non-goals and the deferred decisions.)

### Users and other stakeholders

(Each group of users first, and then every other stakeholder, including those who never chose to be one.)

- **(Group)**: (What they need from the system, and the constraints that they impose on it, down to the most constrained environment it must run in. For users, the leading alternative and, where it serves them better, what the system offers them instead. Where other stakeholders must trust the group (e.g., operators), with what.)

## Principles

(What every change must comply with, in order of priority, so that the order settles any conflict. A principle may serve one group, several, or the system as a whole.)

### (Principle, as a rule that a change could break)

(Why it matters, what it optimises for, and at the expense of what.)

## Components

(A diagram of the components and who interacts with them.)

- **(Component)**: (Which groups of users interact with it, what it knows about the people it serves, and whom it trusts with what.)

## Dependencies

(Whatever the design relies on beyond itself. For each one, say what stakeholders must trust the party behind it with and, where anonymity or deniability is a requirement, what that party could be compelled to disclose, alter, or block. Where anonymity depends on a crowd, give its size.)

### Backing services

(Wherever someone else could deploy the system. Where it's coupled to one provider, say so, along with the layers that are deliberately not portable.)

- **(Backing service, by the capability it provides)**: (What the design relies on it for.)

### Delegations

- **(Provider, platform, or third-party software)**: (What is delegated to it, and the limit, caveat, or dependency that this imposes.)

### Legal and contractual obligations

- **(Obligation)**: (What the design relies on it for, and what happens if it's breached.)

## Relevant standards

- **(Standard)**: (The part of the design that it could serve, whether it's adopted, and why.)

## Impact on stakeholders

(Who the design leaves worse off, and how.)

### Limitations

- **(Limitation)**: (Who bears it, and the workaround, if there is one.)

### Ethical costs

(Those that the design can't discharge, including to people who aren't users and to the environment.)

- **(Cost)**: (Who bears it, and why the design can't discharge it.)

### Residual risks

(Including a link to the threat model.)
