# Prototyping

A _prototype_ is code written to answer a question, and discarded once it has answered it. Every rule in the skill applies, except as follows.

- The effort MUST go into the parts whose feasibility is in doubt. Parts already known to work MUST be left out or stubbed.
- Units MUST NOT be tested individually. The artefact MUST be tested from the outside instead, in the environment it's meant to run in: an end-user application through what a user would do, a server-side application through what a client would do, and a library through what a consuming application would do.
- Those tests MUST cover the main journeys, and nothing else.
- A path outside the main journeys MAY be left unimplemented. Where one is, the code MUST fail immediately and state that the case is unsupported, so that the gap can't be mistaken for a defect.
