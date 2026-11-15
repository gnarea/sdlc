# Continuous delivery

These apply to every artefact, whether it's published to a registry, submitted to a store, or deployed.

- A merge to the default branch MUST release the artefact automatically if and only if the merge changes what ships (e.g., an update to a dependency only does where the dependency ships inside the artefact), and CI MUST check this before the change merges.
- The version and the release notes MUST be derived from the commit history (e.g., from Conventional Commits), never set by hand, and the notes MUST fit each destination's limits (e.g., an app store's character limit).
- Every artefact MUST be released exactly as it was tested, rather than built again for the release. Where it can only be signed by the pipeline that releases it, that pipeline MUST test the signed artefact before releasing it.
- Every artefact that can be signed MUST be signed, with the CI platform's identity where its consumers can verify one (e.g., keyless signing), rather than with a long-lived key. Where a long-lived key is needed and the destination can hold it (e.g., Google Play), the destination MUST hold it, and the pipeline MUST only hold a credential that the destination can revoke (e.g., an upload key).
- Each release MUST be immutable, with an exact version, and whatever deploys it MUST pin that version, so that each upgrade is a change that's checked like any other.
- Each release MUST be published to every registry that its consumers' platforms pull from.
- A release MUST only become visible once every part of it is published (e.g., each operating system's installer).
- Releases of the same artefact MUST run one at a time, in order.
- The documentation for each release MUST be published when the release is, wherever the documentation is kept, so that it matches what was released.
