import ast
import json
import re
import time
from pathlib import Path

from tests.direct.test_source_quorum_semantic_consensus import (
    body,
    build_scenario,
    create_structured_review,
    deploy_contract,
    digest,
    mock_semantic,
    mock_web,
)


def make_admissible(
    contract,
    direct_vm,
):
    scenario = build_scenario(
        contract
    )

    structured = (
        create_structured_review(
            contract,
            direct_vm,
            scenario,
        )
    )

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
    )

    admissible = (
        contract.
        review_semantic_independence(
            structured
        )
    )

    assert (
        contract.get_review_status(
            admissible
        )
        == "ADMISSIBLE"
    )

    direct_vm.clear_mocks()

    return (
        scenario,
        structured,
        admissible,
    )


def counter_payload(
    fact="NO",
):
    published_at = (
        int(time.time()) - 10
    )

    return body(
        "counter-v1",
        published_at,
        fact,
        (
            "Approved authority reports "
            f"{fact} in counter-evidence."
        ),
        (
            "First-party counter-evidence "
            "from the approved authority."
        ),
    )


def counter_url(
    scenario,
):
    origin = (
        scenario[
            "locations"
        ]["a"].rsplit(
            "/",
            1,
        )[0]
    )

    return (
        origin
        + "/challenge/counter-v1"
    )


def submit_counter(
    contract,
    scenario,
    payload,
):
    return (
        contract.
        submit_challenge_request(
            scenario["bundle"],
            scenario[
                "corroborator_a"
            ],
            1,
            counter_url(
                scenario
            ),
            "counter-v1",
            digest(
                payload
            ),
            (
                "Counter-evidence may materially "
                "undermine the current review."
            ),
        )
    )


def mock_counter_web(
    direct_vm,
    scenario,
    payload,
    status=200,
):
    direct_vm.mock_web(
        re.escape(
            counter_url(
                scenario
            )
        ),
        {
            "status": status,
            "body": payload,
        },
    )


def mock_materiality(
    direct_vm,
    classification,
):
    if classification == "MATERIAL":
        basis = (
            "DIRECT_FACTUAL_CONTRADICTION"
        )

    elif classification == "IMMATERIAL":
        basis = (
            "NO_MATERIAL_CONFLICT"
        )

    else:
        basis = (
            "MATERIALITY_UNVERIFIED"
        )

    direct_vm.mock_llm(
        (
            r"(?s).*SourceQuorum "
            r"challenge materiality review.*"
        ),
        json.dumps(
            {
                "classification":
                    classification,
                "basis_code":
                    basis,
            }
        ),
    )


def test_material_challenge_opens_exact_target_and_preserves_evidence_pointer(
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

    assert (
        contract.
        get_challenge_target_review_id(
            challenge_id
        )
        == admissible
    )

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "MATERIAL",
    )

    challenge_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_review_kind(
            challenge_review
        )
        == "challenge"
    )

    assert (
        contract.
        get_review_challenge_request_id(
            challenge_review
        )
        == challenge_id
    )

    assert (
        contract.get_review_status(
            challenge_review
        )
        == "CONFLICTED"
    )

    assert (
        contract.get_review_reason_code(
            challenge_review
        )
        == "CHALLENGE_MATERIAL_CONFLICT"
    )

    assert (
        contract.
        get_review_conflict_detected(
            challenge_review
        )
    )

    assert not (
        contract.
        bundle_has_pending_challenge_request(
            scenario["bundle"]
        )
    )

    assert (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    # CRITICAL:
    # challenge review must never replace the latest evidence pointer.
    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )

    assert (
        contract.
        get_latest_challenge_review_id(
            scenario["bundle"]
        )
        == challenge_review
    )

    assert (
        contract.get_latest_review_id(
            scenario["bundle"]
        )
        == challenge_review
    )

    assert (
        contract.get_review_previous_id(
            challenge_review
        )
        == admissible
    )


def test_immaterial_challenge_closes_pending_without_opening(
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
        "YES"
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        payload,
    )

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "IMMATERIAL",
    )

    challenge_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_review_status(
            challenge_review
        )
        == "INADMISSIBLE"
    )

    assert (
        contract.get_review_reason_code(
            challenge_review
        )
        == "CHALLENGE_IMMATERIAL"
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    assert not (
        contract.
        bundle_has_pending_challenge_request(
            scenario["bundle"]
        )
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )

    assert (
        contract.
        get_latest_challenge_review_id(
            scenario["bundle"]
        )
        == challenge_review
    )


def test_unavailable_challenge_evidence_cannot_open_bundle(
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

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
        status=503,
    )

    challenge_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_review_status(
            challenge_review
        )
        == "UNAVAILABLE"
    )

    assert (
        contract.get_review_reason_code(
            challenge_review
        )
        == "CHALLENGE_EVIDENCE_UNAVAILABLE"
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    # Transient unavailability must NOT silently dispose of the
    # exact pending request.
    assert (
        contract.
        bundle_has_pending_challenge_request(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_pending_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )

    unavailable_review = (
        challenge_review
    )

    # Retry the SAME immutable challenge once its exact evidence
    # becomes available.
    direct_vm.clear_mocks()

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "MATERIAL",
    )

    material_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_review_status(
            material_review
        )
        == "CONFLICTED"
    )

    assert (
        contract.get_review_previous_id(
            material_review
        )
        == unavailable_review
    )

    assert not (
        contract.
        bundle_has_pending_challenge_request(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )


def test_digest_changed_counter_evidence_cannot_open_bundle(
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

    submitted_payload = (
        counter_payload(
            "NO"
        )
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        submitted_payload,
    )

    changed_payload = body(
        "counter-v1",
        int(time.time()) - 10,
        "YES",
        "Changed after challenge submission.",
        "Changed provenance payload.",
    )

    mock_counter_web(
        direct_vm,
        scenario,
        changed_payload,
    )

    challenge_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_review_status(
            challenge_review
        )
        == "INADMISSIBLE"
    )

    assert (
        contract.get_review_reason_code(
            challenge_review
        )
        == "CHALLENGE_EVIDENCE_CHANGED"
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )


def test_validator_rejects_different_challenge_materiality(
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
        _admissible,
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

    # Leader.
    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "MATERIAL",
    )

    contract.review_challenge_materiality(
        challenge_id
    )

    # Validator independently sees the same bytes but reaches a
    # different consequential classification.
    direct_vm.clear_mocks()

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "IMMATERIAL",
    )

    assert (
        direct_vm.run_validator()
        is False
    )


def test_target_zero_cannot_be_materialized_against_later_review(
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

    payload = counter_payload(
        "NO"
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        payload,
    )

    assert (
        contract.
        get_challenge_target_review_id(
            challenge_id
        )
        == 0
    )

    with direct_vm.expect_revert(
        "Challenge request has no evidence review target"
    ):
        contract.review_challenge_materiality(
            challenge_id
        )

    assert (
        contract.
        bundle_has_pending_challenge_request(
            scenario["bundle"]
        )
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )


def test_immaterial_structured_target_allows_semantic_completion_without_pointer_drift(
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

    structured = (
        create_structured_review(
            contract,
            direct_vm,
            scenario,
        )
    )

    payload = counter_payload(
        "YES"
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        payload,
    )

    assert (
        contract.
        get_challenge_target_review_id(
            challenge_id
        )
        == structured
    )

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "IMMATERIAL",
    )

    challenge_review = (
        contract.
        review_challenge_materiality(
            challenge_id
        )
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == structured
    )

    assert (
        contract.get_latest_review_id(
            scenario["bundle"]
        )
        == challenge_review
    )

    direct_vm.clear_mocks()

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
    )

    semantic = (
        contract.
        review_semantic_independence(
            structured
        )
    )

    assert (
        contract.get_review_status(
            semantic
        )
        == "ADMISSIBLE"
    )

    # Global append-only lineage includes the intervening challenge
    # review, while semantic input identity remains the structured
    # evidence review.
    assert (
        contract.get_review_previous_id(
            semantic
        )
        == challenge_review
    )

    assert (
        contract.
        get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == semantic
    )


def test_open_challenge_cannot_be_expired_as_pending_request(
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
        _admissible,
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

    mock_counter_web(
        direct_vm,
        scenario,
        payload,
    )

    mock_materiality(
        direct_vm,
        "MATERIAL",
    )

    contract.review_challenge_materiality(
        challenge_id
    )

    with direct_vm.expect_revert(
        "Open challenge cannot expire as a pending request"
    ):
        contract.expire_challenge_request(
            challenge_id
        )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    assert not (
        contract.is_challenge_request_expired(
            challenge_id
        )
    )


def test_open_challenge_writers_are_protocol_only():
    source = Path(
        "contracts/source_quorum.py"
    ).read_text()

    tree = ast.parse(
        source
    )

    writers = []

    for fn in [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.FunctionDef,
        )
    ]:
        for node in ast.walk(fn):
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
                if not isinstance(
                    target,
                    ast.Subscript,
                ):
                    continue

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
                    and value.value.id
                    == "self"
                    and value.attr
                    == "bundle_open_challenge_id"
                ):
                    writers.append(
                        fn.name
                    )

    assert writers == [
        "review_challenge_materiality",
        "review_open_challenge_resolution",
    ]



def test_claimant_reason_is_not_fed_to_materiality_model():
    source = Path(
        "contracts/source_quorum.py"
    ).read_text()

    tree = ast.parse(
        source
    )

    matches = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name
            == "review_challenge_materiality"
        )
    ]

    assert len(matches) == 1

    segment = ast.get_source_segment(
        source,
        matches[0],
    )

    assert (
        "challenge_memory.reason"
        not in segment
    )

    assert (
        "submitted challenge reason"
        not in segment.lower()
    )
