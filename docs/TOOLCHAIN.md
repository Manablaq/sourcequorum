# SourceQuorum Toolchain

## Verified baseline

Python:

```
3.12.14
```

The official GenLayer project boilerplate was cloned and installed
unchanged on 2026-08-24. Its Git branch references resolved to:

- genlayer-py branch `v0.18`
  - a3dc35e04898e3889cbfa855bcaf7d2664675b8f
- genlayer-testing-suite branch `v0.29`
  - 9c09578b143905471fb0657dd53bdaf18da8e35f
- genvm-linter branch `main`
  - fa4a4d4536b28fdc2730e13a983ba01b69ccc6f3

The untouched official Direct Mode control suite completed successfully
before these immutable revisions were adopted by SourceQuorum.

## GenVM dependency header

```
py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6
```

## Reproduction

Create a Python 3.12 virtual environment and install:

```bash
python -m pip install -r requirements-lock.txt
python -m pip check
```

Reviewer-facing reproduction must use `requirements-lock.txt`.

No GenLayer dependency revision may change without rerunning the
complete deterministic, consensus, supported-runtime, and release
verification gates applicable at that stage.

## Current verification state

As of 2026-08-25, Python 3.12.14 is in use and the complete SourceQuorum Direct Mode suite passes 75/75 tests, including adversarial evidence resource-bound and prompt-boundary coverage. Bradbury supported-runtime consensus mechanism verification is complete. SourceQuorum deployment, deployed contract-path verification, and live finality verification remain pending.
