# Bradbury Supported-Runtime Verification

Date: 2026-08-25

SourceQuorum includes a reproducible Bradbury `gen_call` harness at:

`python scripts/verify_supported_runtime_consensus.py`

## Verified behavior

The harness executes GenVM leader and validator modes against the Bradbury RPC.

Agreement case:

- leader execution succeeds
- leader returns exactly one `eqOutput`
- the exact leader output is supplied as `leader_results`
- validator execution succeeds
- validator `eqOutputs` is empty
- `nondetDisagreementCallNo` is `null`

Same-source rejection case:

- leader and validator use identical contract source
- leader execution succeeds and produces one `eqOutput`
- validator deliberately rejects that leader result
- validator execution succeeds
- validator `eqOutputs` is empty
- `nondetDisagreementCallNo` is `0`

The harness writes each HTTP response as raw bytes before JSON decoding.

Generated requests and raw responses are reproducible local evidence and are not committed.

## Scope

This verifies the Bradbury GenVM leader/validator `gen_call` mechanism used by SourceQuorum's consensus design.

It is not evidence that the production SourceQuorum contract has already been deployed or that its live evidence-review paths have reached network finality. Those checks remain mandatory after deployment.

The complete SourceQuorum Direct Mode suite currently passes 75/75 tests.
