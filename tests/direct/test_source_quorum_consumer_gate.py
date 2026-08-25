import ast
from pathlib import Path

from tests.direct.test_source_quorum_challenge_materiality import (
    counter_payload,
    make_admissible,
    submit_counter,
)
from tests.direct.test_source_quorum_challenge_resolution import (
    mock_resolution,
    open_material_challenge,
    resolution_payload,
    review_resolution,
)
from tests.direct.test_source_quorum_semantic_consensus import (
    build_scenario,
    create_structured_review,
    deploy_contract,
    mock_web,
)


def test_admissible_bundle_exposes_exact_current_review(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    bundle = scenario["bundle"]

    assert contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == admissible
    )

    assert contract.is_review_currently_admissible(
        admissible
    )


def test_structured_candidate_is_never_currently_admissible(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_scenario(
        contract
    )

    structured = create_structured_review(
        contract,
        direct_vm,
        scenario,
    )

    bundle = scenario["bundle"]

    assert (
        contract.get_review_status(
            structured
        )
        == "INADMISSIBLE"
    )

    assert not contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == 0
    )

    assert not contract.is_review_currently_admissible(
        structured
    )


def test_pending_challenge_request_is_nonconsequential_for_consumer_gate(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    payload = counter_payload(
        "NO"
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        payload,
    )

    bundle = scenario["bundle"]

    assert (
        contract.get_pending_challenge_id(
            bundle
        )
        == challenge_id
    )

    assert (
        contract.get_open_challenge_id(
            bundle
        )
        == 0
    )

    # SECURITY:
    # Unreviewed challenge submission alone cannot grief-block
    # consequential consumers.
    assert contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == admissible
    )


def test_validator_confirmed_open_challenge_blocks_consumer_gate(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        admissible,
        challenge_id,
        _material_review,
        _challenged_payload,
    ) = open_material_challenge(
        contract,
        direct_vm,
    )

    bundle = scenario["bundle"]

    assert (
        contract.get_open_challenge_id(
            bundle
        )
        == challenge_id
    )

    assert not contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == 0
    )

    assert not contract.is_review_currently_admissible(
        admissible
    )


def test_validator_backed_retraction_restores_same_fresh_evidence_review(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        admissible,
        challenge_id,
        _material_review,
        challenged_payload,
    ) = open_material_challenge(
        contract,
        direct_vm,
    )

    bundle = scenario["bundle"]

    assert not contract.is_bundle_currently_admissible(
        bundle
    )

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        action="RETRACT",
    )

    mock_resolution(
        direct_vm,
        scenario,
        payload,
    )

    review_resolution(
        contract,
        scenario,
        challenge_id,
        payload,
    )

    assert (
        contract.get_open_challenge_id(
            bundle
        )
        == 0
    )

    # Resolution clears the exact challenge. It does not manufacture a
    # replacement evidence review. The original immutable evidence review
    # becomes usable again only because all current-use invariants still hold.
    assert (
        contract.get_latest_evidence_review_id(
            bundle
        )
        == admissible
    )

    assert contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == admissible
    )

    assert contract.is_review_currently_admissible(
        admissible
    )


def test_superseding_bundle_invalidates_historical_admissibility(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    old_bundle = scenario["bundle"]

    assert contract.is_bundle_currently_admissible(
        old_bundle
    )

    new_bundle = contract.create_superseding_bundle(
        old_bundle
    )

    assert (
        contract.get_bundle_superseded_by(
            old_bundle
        )
        == new_bundle
    )

    # Historical evidence remains auditable but can no longer authorize
    # a current consequential consumer.
    assert not contract.is_bundle_currently_admissible(
        old_bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            old_bundle
        )
        == 0
    )

    assert not contract.is_review_currently_admissible(
        admissible
    )

    # A fresh successor has no authority until independently reviewed.
    assert not contract.is_bundle_currently_admissible(
        new_bundle
    )


def test_newer_evidence_review_invalidates_old_admissible_review(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    bundle = scenario["bundle"]

    assert contract.is_review_currently_admissible(
        admissible
    )

    mock_web(
        direct_vm,
        scenario,
    )

    newer_structured = contract.review_frozen_bundle(
        bundle
    )

    direct_vm.clear_mocks()

    assert (
        newer_structured
        != admissible
    )

    assert (
        contract.get_latest_evidence_review_id(
            bundle
        )
        == newer_structured
    )

    assert (
        contract.get_review_status(
            newer_structured
        )
        == "INADMISSIBLE"
    )

    # A historical ADMISSIBLE status is not a permanent permit.
    assert not contract.is_review_currently_admissible(
        admissible
    )

    assert not contract.is_bundle_currently_admissible(
        bundle
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle
        )
        == 0
    )


def test_consumer_gate_is_deterministic_fail_closed_and_freshness_bound():
    source = Path(
        "contracts/source_quorum.py"
    ).read_text()

    tree = ast.parse(
        source
    )

    methods = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }

    gate = methods[
        "_current_admissible_review_id"
    ]

    gate_source = ast.unparse(
        gate
    )

    required = (
        "bundle_latest_evidence_review_id",
        "bundle_superseded_by",
        "bundle_open_challenge_id",
        "REVIEW_ADMISSIBLE",
        "SEMANTIC_INDEPENDENCE_CONFIRMED",
        "maximum_evidence_age",
        "claimed_published_at",
        "verified_primary_published_at",
        "qualifying_authority_set",
        "independent_corroborator_count",
        "_authority_is_currently_valid",
        "policy_authority_membership",
        "_now",
    )

    for needle in required:
        assert needle in gate_source

    # Submission alone must remain non-consequential.
    assert (
        "bundle_pending_challenge_id"
        not in gate_source
    )

    # Current-use checking must never introduce a new nondeterministic
    # consequence or external observation.
    for forbidden in (
        "gl.nondet",
        "run_nondet_unsafe",
        "exec_prompt",
        "web.get",
        "web.request",
    ):
        assert forbidden not in gate_source

    # The helper is read-only: it may inspect storage but may not assign to
    # persistent SourceQuorum maps/fields.
    persistent_writes = []

    for node in ast.walk(
        gate
    ):
        targets = []

        if isinstance(
            node,
            ast.Assign,
        ):
            targets.extend(
                node.targets
            )
        elif isinstance(
            node,
            ast.AnnAssign,
        ):
            targets.append(
                node.target
            )
        elif isinstance(
            node,
            ast.AugAssign,
        ):
            targets.append(
                node.target
            )

        for target in targets:
            if isinstance(
                target,
                ast.Attribute,
            ) and isinstance(
                target.value,
                ast.Name,
            ) and target.value.id == "self":
                persistent_writes.append(
                    ast.unparse(target)
                )

            if isinstance(
                target,
                ast.Subscript,
            ):
                value = target.value

                if (
                    isinstance(
                        value,
                        ast.Attribute,
                    )
                    and isinstance(
                        value.value,
                        ast.Name,
                    )
                    and value.value.id == "self"
                ):
                    persistent_writes.append(
                        ast.unparse(target)
                    )

    assert persistent_writes == []

    print(
        "CONSUMER GATE SECURITY MODEL: PASS"
    )



def test_current_admissibility_expires_at_exact_evidence_freshness_boundary(
    direct_vm,
    direct_deploy,
    monkeypatch,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    bundle_id = scenario[
        "bundle"
    ]

    assert contract.is_bundle_currently_admissible(
        bundle_id
    )

    bundle = contract._require_bundle(
        bundle_id
    )

    review = contract._require_review(
        admissible
    )

    policy = contract._require_policy(
        bundle.policy_id,
        bundle.policy_version,
    )

    maximum_age = int(
        policy.maximum_evidence_age
    )

    assert maximum_age > 0

    qualifying = set(
        review.qualifying_authority_set.split(
            "|"
        )
    )

    assert qualifying

    relevant_published_at = []

    bundle_key = contract._bundle_key(
        bundle.bundle_id
    )

    for index in range(
        1,
        int(bundle.record_count) + 1,
    ):
        record_id = (
            contract.bundle_record_ids.get(
                f"{bundle_key}|{index}",
                0,
            )
        )

        assert int(record_id) > 0

        record = contract.records[
            contract._record_key(
                record_id
            )
        ]

        identity = (
            str(
                int(
                    record.authority_id
                )
            )
            + ":"
            + str(
                int(
                    record.authority_revision
                )
            )
        )

        contributes = (
            record.record_id
            == bundle.primary_record_id
            or identity in qualifying
        )

        if not contributes:
            continue

        # Keep this regression specifically about evidence freshness.
        # If an authority has a finite validity horizon, it must not
        # expire before the evidence freshness boundary under test.
        authority = contract._require_authority(
            record.authority_id,
            record.authority_revision,
        )

        published_at = int(
            record.claimed_published_at
        )

        assert published_at > 0

        evidence_expiry = (
            published_at
            + maximum_age
        )

        valid_until = int(
            authority.valid_until
        )

        assert (
            valid_until == 0
            or valid_until > evidence_expiry
        )

        relevant_published_at.append(
            published_at
        )

    assert relevant_published_at

    # Current admissibility expires as soon as the oldest piece of
    # evidence that actually contributed to the semantic quorum exceeds
    # the exact policy maximum age.
    first_expiry = min(
        published_at
        + maximum_age
        for published_at
        in relevant_published_at
    )

    clock_type = type(
        contract._now()
    )

    monkeypatch.setattr(
        contract,
        "_now",
        lambda: clock_type(
            first_expiry
        ),
        raising=False,
    )

    # The contract uses:
    #
    #     now - published_at > maximum_age
    #
    # so the exact boundary remains valid.
    assert contract.is_bundle_currently_admissible(
        bundle_id
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle_id
        )
        == admissible
    )

    assert contract.is_review_currently_admissible(
        admissible
    )

    monkeypatch.setattr(
        contract,
        "_now",
        lambda: clock_type(
            first_expiry + 1
        ),
        raising=False,
    )

    # One second beyond the earliest contributing evidence deadline,
    # historical ADMISSIBLE state must no longer authorize use.
    assert not contract.is_bundle_currently_admissible(
        bundle_id
    )

    assert (
        contract.get_current_admissible_review_id(
            bundle_id
        )
        == 0
    )

    assert not contract.is_review_currently_admissible(
        admissible
    )
