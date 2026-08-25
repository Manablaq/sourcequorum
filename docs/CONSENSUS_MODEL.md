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

## Bounded evidence enumeration

SourceQuorum v1 permits at most 16 evidence records in one bundle.

This is a SourceQuorum protocol limit, not a GenLayer platform limit.

The purpose is to keep every review attempt bounded and reproducible:

- one primary record
- up to fifteen corroborating records
- deterministic bundle-indexed enumeration
- no scan over unrelated global evidence records
- bounded external requests per validator

`bundle_record_ids` is an immutable 1-based bundle-local index populated
only when an evidence record is added.

Because frozen bundles reject further record additions, the indexed
evidence set reviewed by validators cannot change after bundle freeze.

A policy whose minimum independent corroborator requirement cannot fit
within the v1 bundle limit is rejected when the policy version is
created.

## Structured-review independence boundary

The structured evidence layer verifies objective evidence properties but
does not itself prove semantic or provenance independence.

It may deterministically calculate a structural candidate count while
evaluating whether the submitted bundle could potentially meet its
policy quorum.

That candidate count is not the final independent corroborator count.

Until validator-backed semantic/provenance review establishes that the
candidate authorities independently establish the fact rather than copy
the same upstream source, a structured ReviewRecord must persist:

- `independent_corroborator_count = 0`
- empty final `qualifying_authority_set`
- empty final `excluded_authority_set`

The structured layer therefore cannot make a bundle `ADMISSIBLE`.

This prevents structural diversity, separate domains, or separate
authority IDs from being mistaken for genuinely independent evidence.

## Exact provenance binding

A semantic relationship label alone is insufficient for consequential
independence.

For every corroborator, semantic consensus binds:

- exact authority revision
- relationship: `INDEPENDENT`, `DERIVED`, or `UNVERIFIED`
- exact provenance basis code
- exact upstream authority revision when derived
- material-conflict flag

An `INDEPENDENT` classification requires an accepted independent basis
and no upstream authority.

A `DERIVED` classification must identify another exact authority
revision supplied in the bundle. Self-dependency is invalid.

If an apparent dependency cannot be safely bound to a supplied
authority, the result is `UNVERIFIED` and the source does not count
toward quorum.

A source's own statement that it is independent is not sufficient
evidence of independence.

Leader and validator must agree on these exact provenance fields.
The contract, not the LLM, derives the qualifying authority set,
independent quorum count, conflict result, and final admissibility.

## Challenge evidence binding

A challenge request is non-consequential, but its counter-evidence is
still bound before validator materiality review.

Every challenge request identifies:

- the exact frozen bundle and policy version
- an exact authority ID and authority revision
- a location under that authority revision's pre-approved origin
- an explicit immutable/version reference
- a SHA-256 evidence digest
- the submitter's untrusted reason

The authority revision must be sealed, currently valid, and explicitly
approved as either a primary or corroborating authority in the exact
policy version used by the bundle.

An arbitrary user-selected URL or digest is therefore insufficient to
become challenge evidence.

Request submission still has no consequential blocking effect.
It may populate only `bundle_pending_challenge_id`.

Only a later validator-backed materiality review may populate
`bundle_open_challenge_id`.

The free-form challenge reason is an untrusted claimant statement and
must never be treated as authoritative evidence or executable prompt
instructions.
