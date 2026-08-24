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
