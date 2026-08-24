# SourceQuorum v1 Threat Model

## Threats treated as release blockers

1. Correct bytes supplied by an unauthorized or false publisher.
2. Hash integrity incorrectly treated as provenance.
3. Multiple URLs from one authority counted as independent corroboration.
4. Multiple publishers repeating one upstream source counted as independent evidence.
5. Stale evidence accepted because validators agree on old content.
6. Mutable evidence silently changing after adjudication.
7. Owner changing trust rules after seeing evidence.
8. Authority configuration changed retroactively.
9. Leader controlling a consequential fact not independently verified by validators.
10. Validators checking only response shape or allowed enum values.
11. Tolerance allowing validator-compatible results to produce different consequences.
12. Open challenge bypassed through unrelated or unchanged-field update.
13. Counter-evidence unable to trigger a fresh review.
14. Old review remaining usable after evidence expiration.
15. Repository source differing from deployed or submitted Explorer source.
