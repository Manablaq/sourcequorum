# SourceQuorum v1 Specification

Status: implementation specification

## Purpose

SourceQuorum determines whether an exact evidence bundle satisfies an
immutable, precommitted evidence policy strongly enough to become usable
by a consequential downstream decision.

SourceQuorum does not treat URL possession or content hashes alone as
proof of provenance, authority, freshness, or independent corroboration.

## Mandatory v1 properties

- immutable/versioned authority definitions
- immutable/versioned evidence policies
- exact policy-version binding
- immutable frozen evidence bundles
- explicit provenance
- deterministic freshness enforcement
- independent corroboration requirements
- material-conflict fail-closed behavior
- substantive independent validator review
- exact consensus-to-consequence binding
- source-backed challenges
- fresh review after counter-evidence
- challenge bypass resistance
- append-only supersession history
- no stale evidence-use entitlement
- reviewer-facing source/deployment parity

## Implemented security requirements

SourceQuorum v1 bounds fetched evidence to 32 KiB per response body and semantic evidence to 128 KiB per review. Oversized input fails closed before hashing, decoding, JSON parsing, or semantic processing.

Consequential nondeterministic results require exact independent validator agreement. Challenge materiality and challenge resolution are validator-backed, and historical ADMISSIBLE status is not a permanent permit: consumer use re-checks freshness, current authority validity, latest-review identity, supersession, and open-challenge state.
