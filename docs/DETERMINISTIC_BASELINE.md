# SourceQuorum Deterministic Baseline

Historical checkpoint. This file records the deterministic foundation as verified on 2026-08-24; it is not the current project-status document. See `README.md` and `docs/CONSENSUS_MODEL.md` for the current implemented state.

Verified: 2026-08-24

## Scope

This checkpoint contains the deterministic SourceQuorum foundation:

- immutable/versioned authority revisions
- precommitted policy versions
- structural independence-group enforcement
- exact policy-to-authority binding
- approved HTTPS evidence origins
- immutable frozen evidence bundles
- append-only bundle supersession
- non-consequential challenge requests
- challenge-request liveness deadline
- protection against challenge-request griefing changing consequential state

Nondeterministic evidence adjudication and validator consensus are not
part of this checkpoint.

## Verification

Direct Mode is used in-process with no network dependency.

Result:

```
9 passed
```

Python:

```
3.12.14
```

## Source hashes

```
contracts/source_quorum.py
6032fc72b25f46d7e668a36cf8fbe127ab180a6022401a19646bf1608b073ddb

tests/direct/test_source_quorum_deterministic.py
4018de4e0b846690505b3b977b8ebc687b0cf4a653dde824c131a89f5f30595d

requirements-lock.txt
43fd9f7e7219286fc8e75ba13c32e8e79f38b261cdcbc93d2465ddb22aa8f377
```

## GenLayer tooling revisions

```
genlayer-py
a3dc35e04898e3889cbfa855bcaf7d2664675b8f

genlayer-testing-suite
9c09578b143905471fb0657dd53bdaf18da8e35f

genvm-linter
fa4a4d4536b28fdc2730e13a983ba01b69ccc6f3
```

## Security boundary

Submitting counter-evidence does not itself create a consequential open
challenge.

Only a future validator-backed materiality review may create
consequential challenge state.

A digest proves integrity only. It does not establish publisher
authority, provenance, freshness, or factual correctness.
