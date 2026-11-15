# Cloud infrastructure

## Provisioning

- Every resource MUST be declared as code and applied from a repository. Anything provisioned by hand MUST have tracked work to codify or remove it.
- Infrastructure code MUST be partitioned by domain (e.g., access controls, networking, alerts), never by construct type.
- Continuous integration MUST validate all of the code, including any reusable component and its examples, without any credentials for the cloud.
- A rule about infrastructure that can be checked deterministically (e.g., no storage is public, no credential is long-lived) MUST be enforced as policy in continuous integration, rather than left to review.
- Each change MUST show, on the change itself, what applying it would do to the live infrastructure (e.g., which resources it would create, change, or destroy), using an identity that can only read the infrastructure, and MUST NOT merge until that preview has succeeded.
- Merging a change MUST apply it automatically, from a pipeline that alone holds the credentials to do so.

## Least privilege

- Each workload MUST have its own identity, granted only the permissions it uses, enumerated rather than taken wholesale from a predefined role.
- Where the provider supports conditional grants, access MUST be constrained by resource, not only by role.
- A workload MUST obtain its credentials from the platform's identity service where possible, rather than from a stored secret.
- Every service MUST be reachable only by its intended clients.
- The deployment of every server MUST be immutable.

## Cost

- Every estate MUST have a budget, with alerts on both actual and forecast spend.
- Usage that an attacker can drive up and that we can't cap (e.g., inbound traffic at a proxy, DNS lookups) MUST be on an unmetered plan, so that a flood can't run up the bill.
