# Continuous integration

## Every pipeline

These apply whether the pipeline checks a change or delivers an artefact.

- Where two or more codebases produce artefacts of the same type (e.g., npm libraries, container images, Android apps), each stage of their pipelines (e.g., checking a change, releasing) MUST be defined once, in a pipeline that they share and only call. So MUST the configuration that those pipelines need (e.g., the release tool's settings, the checks that a change must pass to merge). A breaking change to a shared pipeline MUST go on a temporary branch until every caller has moved to it.
- A pipeline MUST read whatever its environment already knows (e.g., the default branch, the repository's name, the toolchain's version from the file that developers use locally), rather than hard-code it or take it as a parameter.
- Every external dependency MUST be pinned, including the tools that the pipeline installs and the pipeline's own components (e.g., third-party actions, base images), except a pipeline that the same owner shares, which callers MUST reference at its default branch, so that a fix reaches every caller at once. Where the dependency's ecosystem supports a lockfile (e.g., GitHub Actions' workflow lockfiles), the pin MUST be in it. Otherwise, wherever the publisher can move a version label (e.g., a tag), the pin MUST be a content hash (e.g., a commit hash, an image digest), with the version beside it.
- A bot MUST propose an update to every pin at least every 7 days, and the update MUST be merged automatically once every required check passes, including one that only the versions of existing dependencies changed. Since nobody reviews it, a routine update MUST wait a few days after its release (e.g., 7), so that a malicious release is more likely to be found and pulled before it's adopted. A security fix MUST be proposed as soon as it's released.
- Each credential MUST only be available to the part of the pipeline that uses it, and MUST only grant the permissions that it uses (e.g., on GitHub, the token grants nothing by default, each job is granted what it needs, and the checkout doesn't keep the token for later steps).
- Where the destination supports it, a pipeline MUST obtain its credentials from the CI platform's identity federation, only for the repository, branch, and environment that may use them. A pipeline MUST NOT use a credential tied to a person's account.
- Whatever runs an unreviewed change (e.g., the checks on a pull request) MUST NOT hold a credential that can change any of the artefact's destinations (e.g., publish to a registry, submit to a store, deploy to a cloud).
- Text that an untrusted party controls (e.g., a pull request's title, a branch's name) MUST be passed to scripts as data, never interpolated into their code, and the scripts MUST validate it before using it.
- Whatever holds a credential MUST only run the code that it needs, so that a compromised dependency that's merely installed can't use the credential. In particular, it MUST NOT run its dependencies' install scripts where the package manager can skip them (e.g., with npm's `--ignore-scripts`).
- A pipeline MUST NOT leak a secret, whether through its logs, its caches, or the files that it uploads or publishes.
- A pipeline SHOULD only be able to reach the hosts that it needs (e.g., the registries that it pulls from and publishes to), so that a compromised dependency can't send a secret or the code anywhere else.
- Everything that a pipeline runs MUST have a timeout.
- Scripts MUST stop at the first error (e.g., with strict mode in shell scripts).
- A pipeline MUST NOT wait for a fixed delay: whatever waits for something to happen (e.g., a service to start, an emulator to boot) MUST wait for it to signal that it has.
- A failure that a later attempt could overcome (e.g., a registry's outage, a dropped connection) MUST be retried as close as possible to the operation that failed (e.g., by the package manager, rather than by re-running the pipeline). A test MUST NOT be retried to make it pass, since one that fails intermittently is a defect.
- A failed run MUST keep what's needed to diagnose the failure without running it again (e.g., the logs of every process that it started, the test reports, screenshots).
- A build tool committed to the codebase (e.g., Gradle's wrapper) MUST have its integrity verified before it runs.
- Dependency downloads SHOULD be cached, keyed on the lockfile and the toolchain's version. Where an unreviewed change could write to a cache, and the toolchain doesn't verify each entry against the lockfile's hashes, a pipeline that delivers an artefact MUST NOT restore that cache, since the change could have planted a compromised dependency in it.
- A failure on the default branch MUST be reported where the maintainers will see it (e.g., an issue, an email), so that nobody has to watch the pipeline.
- Every system that a pipeline relies on to deliver an artefact (e.g., the source control, the CI platform, a registry) SHOULD keep an audit log of changes to its permissions and secrets, and of every publication, where the maintainers can review it.

## Checking a change

These apply to the checks that a change must pass before it merges.

- A change MUST only reach the default branch by being merged once every required check has passed, including a dry run of its release, on a branch that's up to date with its base, so that nobody, whether a person or an agent, can push to it directly.
- A required check MUST only accept a result from the CI platform that runs it (e.g., on GitHub, a required check that expects a specific app), so that nobody can mark it as passed by reporting the result themselves.
- Every change MUST be checked in three ways before it merges:
  - Deterministic analysis that finds defects in the code, beyond linting and formatting (e.g., code duplicated across files, dangerous patterns, as found by tools such as SonarQube or Semgrep).
  - Reviews by agents, for what no deterministic check can enforce (e.g., the architecture's conventions, an approach to avoid, a hazard in the threat model), whether the agents come off the shelf (e.g., GitHub Copilot, CodeRabbit) or are written for the codebase.
  - Functional verification: evidence from CI that the change does what it's meant to, and that it doesn't break what it could plausibly affect. Regression testing MUST focus on what the change could plausibly break, rather than on what it clearly can't affect.
- A rule that a deterministic check can enforce (e.g., every dependency is pinned) MUST be enforced by one, rather than left to a review, since a reviewer, whether a person or an agent, may not apply it every time.
- Where checks run across a matrix (e.g., of operating systems or runtime versions), those that can't vary across it (e.g., linting) MUST run once, before or after the matrix, rather than in each of its runs.
