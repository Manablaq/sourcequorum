# SourceQuorum

SourceQuorum is a GenLayer-native evidence admissibility protocol.

It determines whether an exact evidence bundle satisfies a precommitted
authority, provenance, freshness, versioning, conflict, and independent
corroboration policy before that evidence may affect consequential state.

## Status

Initial deterministic protocol implementation in progress.

No Bradbury deployment exists yet.

## Core invariant

Evidence is usable only when the exact frozen evidence bundle satisfies
the exact immutable policy version and GenLayer validators independently
agree on all consequential evidence findings used by deterministic policy
evaluation.

## Development phases

1. Deterministic authority and policy versioning
2. Immutable evidence bundle lifecycle
3. Challenge and supersession invariants
4. Evidence-use permit
5. Independent GenLayer evidence adjudication
6. Adversarial Direct Mode validation
7. Supported-runtime validator verification
8. Bradbury deployment and live finality verification
9. Frontend integration
10. Reviewer-readiness and source/deployment parity audit
