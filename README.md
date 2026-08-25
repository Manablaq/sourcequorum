# SourceQuorum

SourceQuorum is a GenLayer-native evidence admissibility protocol.

It determines whether an exact evidence bundle satisfies a precommitted
authority, provenance, freshness, versioning, conflict, and independent
corroboration policy before that evidence may affect consequential state.

## Status

The v1 Intelligent Contract is implemented and Direct Mode verified.

The complete Direct Mode regression suite passes 75/75 tests as of
2026-08-25, including structured evidence review, semantic provenance
consensus, validator-backed challenge materiality and resolution,
freshness-bound consumer admissibility, resource limits, and adversarial
evidence/prompt tests.

Bradbury supported-runtime consensus mechanism verification is complete; deployed SourceQuorum contract-path verification remains pending.

No Bradbury deployment exists yet.

## Core invariant

Evidence is usable only when the exact frozen evidence bundle satisfies
the exact immutable policy version and GenLayer validators independently
agree on all consequential evidence findings used by deterministic policy
evaluation.

## Current admissibility rule

An `ADMISSIBLE` review is not a permanent permit.

At consumer-use time SourceQuorum re-checks that the exact latest evidence
review is still admissible, the exact bundle has not been superseded, the
bound policy version is still valid for use, the evidence that supports the
decision is still fresh, the contributing authority revisions are still
current and approved for their exact roles, and no validator-confirmed open
challenge exists.

A pending challenge request alone is non-consequential and does not block
consumer use. Only validator-backed materiality may create consequential
open-challenge state.

## Development phases

1. Deterministic authority and policy versioning — complete
2. Immutable evidence bundle lifecycle — complete
3. Append-only evidence review and exact consensus binding — complete
4. Semantic provenance/independence adjudication — complete
5. Validator-backed challenge materiality and resolution — complete
6. Freshness-bound consumer admissibility gate — complete
7. Adversarial Direct Mode validation — complete (75/75)
8. Bradbury supported-runtime consensus mechanism verification — complete
9. Bradbury deployment and live finality verification — pending
10. Frontend integration and reviewer source/deployment parity audit — pending
