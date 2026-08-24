# SourceQuorum Consensus Model

## Purpose

SourceQuorum does not ask validators to agree on free-form reasoning.

Validators must independently derive the exact consequential evidence
facts required to determine whether an evidence bundle is admissible
under its immutable policy version.

## Review attempts are append-only

Every completed review creates a new `ReviewRecord`.

A review is never edited in place.

Each record contains:

- exact bundle ID
- exact policy ID and policy version
- attempt number
- previous review ID
- review kind
- optional challenge-request ID
- deterministic review timestamp
- canonical status
- exact fact code
- exact verified primary record version
- exact verified primary publication timestamp
- exact canonical qualifying authority-revision set
- exact canonical excluded authority-revision set
- exact canonical evidence facts
- deterministically derived independent corroborator count
- material conflict flag
- deterministic reason code

The review ledger is append-only.

## Canonical statuses

The v1 statuses are:

- `ADMISSIBLE`
- `INADMISSIBLE`
- `STALE`
- `CONFLICTED`
- `INSUFFICIENT_CORROBORATION`
- `UNAVAILABLE`

`UNAVAILABLE` represents transient inability to complete a substantive
review. It must not be silently converted into `INADMISSIBLE`.

## Consensus-to-consequence rule

Any field that can alter admissibility, challenge state, permit state,
authorization, entitlement, or another consequential transition must be
bound by validator consensus exactly or derived deterministically from
exact agreed inputs.

Free-form reasoning is not consequential state.

## Authority quorum

Validators do not supply a trusted integer quorum count.

They must agree on the exact qualifying authority-revision identities
and exact evidence facts.

The contract derives the independent corroborator count
deterministically from that exact canonical set.

## Freshness

Claimant-supplied `claimed_published_at` is not authoritative freshness
evidence.

Validators must independently establish actual publication/version
metadata.

The contract then compares the verified timestamp against the immutable
policy's maximum evidence age using deterministic transaction time.

## Conflict

Material authoritative conflict fails closed.

A materially conflicting evidence bundle cannot become `ADMISSIBLE`.

## Nondeterministic boundary

Before nondeterministic execution:

1. load the exact frozen bundle
2. load the exact immutable policy version
3. load the exact authority revisions
4. load the exact evidence records
5. copy storage-backed objects to memory

Inside nondeterministic execution:

- fetch evidence
- verify record/version metadata
- derive factual result
- evaluate provenance/semantic independence
- detect material conflict

No storage writes occur inside nondeterministic execution.

After consensus returns:

- validate the exact agreed result
- canonicalize consequential sets
- derive quorum deterministically
- calculate freshness deterministically
- derive final status
- append one immutable ReviewRecord

## Validator independence

Validators must re-fetch/re-review the evidence themselves.

A validator that checks only JSON shape or leader-supplied conclusions
is insufficient.

Direct Mode tests must replace leader web/LLM mocks before
`run_validator()` and prove disagreement when the validator sees
different consequential evidence.
