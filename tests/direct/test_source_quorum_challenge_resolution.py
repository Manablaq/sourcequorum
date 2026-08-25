import json
import re
import time

import pytest

from tests.direct.test_source_quorum_challenge_materiality import (
    counter_payload,
    digest,
    make_admissible,
    mock_counter_web,
    mock_materiality,
    submit_counter,
)
from tests.direct.test_source_quorum_semantic_consensus import (
    deploy_contract,
)


def open_material_challenge(
    contract,
    direct_vm,
):
    (
        scenario,
        _structured,
        admissible,
    ) = make_admissible(
        contract,
        direct_vm,
    )

    challenged_payload = (
        counter_payload("NO")
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        challenged_payload,
    )

    mock_counter_web(
        direct_vm,
        scenario,
        challenged_payload,
    )

    mock_materiality(
        direct_vm,
        "MATERIAL",
    )

    material_review = (
        contract.review_challenge_materiality(
            challenge_id
        )
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    direct_vm.clear_mocks()

    # Direct Mode contract time and host wall-clock time
    # are different clock domains. Resolution evidence must
    # use the same clock domain that the contract uses for its
    # freshness/future-date checks.
    scenario[
        "_resolution_published_at"
    ] = int(
        contract._now()
    )

    return (
        scenario,
        admissible,
        challenge_id,
        material_review,
        challenged_payload,
    )


def resolution_url(
    scenario,
):
    origin = (
        scenario["locations"]["a"].
        rsplit("/", 1)[0]
    )

    return (
        origin
        + "/challenge-resolution/v2"
    )


def resolution_payload(
    scenario,
    challenge_id,
    target_review_id,
    challenged_payload,
    action="RETRACT",
    published_at=None,
    overrides=None,
):
    if published_at is None:
        if (
            "_resolution_published_at"
            not in scenario
        ):
            raise AssertionError(
                "resolution fixture missing "
                "contract-clock timestamp"
            )

        published_at = int(
            scenario[
                "_resolution_published_at"
            ]
        )

    data = {
        "version_reference":
            "resolution-v2",
        "published_at":
            published_at,
        "resolution_action":
            action,
        "resolves_challenge_id":
            challenge_id,
        "target_review_id":
            target_review_id,
        "target_fact_code":
            "YES",
        "authority_id":
            scenario[
                "corroborator_a"
            ],
        "authority_revision":
            1,
        "supersedes_version_reference":
            "counter-v1",
        "supersedes_digest":
            digest(
                challenged_payload
            ),
    }

    if overrides:
        data.update(
            overrides
        )

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    )


def mock_resolution(
    direct_vm,
    scenario,
    payload,
    status=200,
):
    direct_vm.mock_web(
        re.escape(
            resolution_url(
                scenario
            )
        ),
        {
            "status": status,
            "body": payload,
        },
    )


def review_resolution(
    contract,
    scenario,
    challenge_id,
    payload,
):
    return (
        contract.review_open_challenge_resolution(
            challenge_id,
            resolution_url(
                scenario
            ),
            "resolution-v2",
            digest(payload),
        )
    )


def test_fresh_retract_clears_exact_open_challenge_and_preserves_evidence_pointer(
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
        material_review,
        challenged_payload,
    ) = open_material_challenge(
        contract,
        direct_vm,
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

    resolution_review = (
        review_resolution(
            contract,
            scenario,
            challenge_id,
            payload,
        )
    )

    assert not (
        contract.bundle_has_open_challenge(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == 0
    )

    assert (
        contract.get_review_kind(
            resolution_review
        )
        == "challenge"
    )

    assert (
        contract.get_review_challenge_request_id(
            resolution_review
        )
        == challenge_id
    )

    assert (
        contract.get_review_status(
            resolution_review
        )
        == "INADMISSIBLE"
    )

    assert (
        contract.get_review_reason_code(
            resolution_review
        )
        == "CHALLENGE_RETRACTED_BY_AUTHORITY"
    )

    assert not (
        contract.get_review_conflict_detected(
            resolution_review
        )
    )

    assert (
        contract.get_review_previous_id(
            resolution_review
        )
        == material_review
    )

    # Challenge-resolution history must not rewrite evidence identity.
    assert (
        contract.get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )

    assert (
        contract.get_latest_challenge_review_id(
            scenario["bundle"]
        )
        == resolution_review
    )

    assert (
        contract.get_latest_review_id(
            scenario["bundle"]
        )
        == resolution_review
    )


def test_uphold_keeps_exact_challenge_open(
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

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        action="UPHOLD",
    )

    mock_resolution(
        direct_vm,
        scenario,
        payload,
    )

    review_id = review_resolution(
        contract,
        scenario,
        challenge_id,
        payload,
    )

    assert (
        contract.get_review_status(
            review_id
        )
        == "CONFLICTED"
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "CHALLENGE_REAFFIRMED_BY_AUTHORITY"
    )

    assert (
        contract.get_review_conflict_detected(
            review_id
        )
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    assert (
        contract.get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )


def test_unavailable_resolution_keeps_open_and_can_retry_same_record(
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

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
    )

    mock_resolution(
        direct_vm,
        scenario,
        payload,
        status=503,
    )

    unavailable_review = (
        review_resolution(
            contract,
            scenario,
            challenge_id,
            payload,
        )
    )

    assert (
        contract.get_review_status(
            unavailable_review
        )
        == "UNAVAILABLE"
    )

    assert (
        contract.get_review_reason_code(
            unavailable_review
        )
        == "CHALLENGE_RESOLUTION_UNAVAILABLE"
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )

    direct_vm.clear_mocks()

    mock_resolution(
        direct_vm,
        scenario,
        payload,
    )

    retract_review = (
        review_resolution(
            contract,
            scenario,
            challenge_id,
            payload,
        )
    )

    assert (
        contract.get_review_previous_id(
            retract_review
        )
        == unavailable_review
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == 0
    )

    assert (
        contract.get_latest_evidence_review_id(
            scenario["bundle"]
        )
        == admissible
    )


def test_changed_resolution_bytes_cannot_clear_open_challenge(
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

    submitted_payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
    )

    changed_payload = (
        submitted_payload + " "
    )

    mock_resolution(
        direct_vm,
        scenario,
        changed_payload,
    )

    review_id = (
        contract.review_open_challenge_resolution(
            challenge_id,
            resolution_url(
                scenario
            ),
            "resolution-v2",
            digest(
                submitted_payload
            ),
        )
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "CHALLENGE_RESOLUTION_EVIDENCE_CHANGED"
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )


@pytest.mark.parametrize(
    "binding_field",
    [
        "resolves_challenge_id",
        "target_review_id",
        "authority_id",
        "authority_revision",
        "supersedes_version_reference",
        "supersedes_digest",
    ],
)
def test_wrong_resolution_binding_cannot_clear_open_challenge(
    direct_vm,
    direct_deploy,
    binding_field,
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

    wrong_values = {
        "resolves_challenge_id":
            challenge_id + 999,
        "target_review_id":
            admissible + 999,
        "authority_id":
            scenario[
                "corroborator_a"
            ] + 999,
        "authority_revision":
            999,
        "supersedes_version_reference":
            "counter-wrong-version",
        "supersedes_digest":
            "sha256:" + "0" * 64,
    }

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        overrides={
            binding_field:
                wrong_values[
                    binding_field
                ]
        },
    )

    mock_resolution(
        direct_vm,
        scenario,
        payload,
    )

    review_id = review_resolution(
        contract,
        scenario,
        challenge_id,
        payload,
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "CHALLENGE_RESOLUTION_INVALID_BINDING"
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )


def test_stale_resolution_record_cannot_clear_open_challenge(
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

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        published_at=(
            int(time.time())
            - 90000
        ),
    )

    mock_resolution(
        direct_vm,
        scenario,
        payload,
    )

    review_id = review_resolution(
        contract,
        scenario,
        challenge_id,
        payload,
    )

    assert (
        contract.get_review_status(
            review_id
        )
        == "STALE"
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "CHALLENGE_RESOLUTION_STALE"
    )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )


def test_validator_disagreement_cannot_authorize_resolution(
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

    retract_payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        action="RETRACT",
    )

    mock_resolution(
        direct_vm,
        scenario,
        retract_payload,
    )

    contract.review_open_challenge_resolution(
        challenge_id,
        resolution_url(
            scenario
        ),
        "resolution-v2",
        digest(
            retract_payload
        ),
    )

    # Validator independently receives different bytes.
    direct_vm.clear_mocks()

    uphold_payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        action="UPHOLD",
    )

    mock_resolution(
        direct_vm,
        scenario,
        uphold_payload,
    )

    assert (
        direct_vm.run_validator()
        is False
    )


def test_non_open_challenge_cannot_use_resolution_path(
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

    challenged_payload = (
        counter_payload("NO")
    )

    challenge_id = submit_counter(
        contract,
        scenario,
        challenged_payload,
    )

    payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
        published_at=int(contract._now()),
    )

    with direct_vm.expect_revert(
        "Challenge is not the bundle open challenge"
    ):
        contract.review_open_challenge_resolution(
            challenge_id,
            resolution_url(
                scenario
            ),
            "resolution-v2",
            digest(
                payload
            ),
        )


def test_resolution_must_be_new_version_and_new_digest(
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

    valid_payload = resolution_payload(
        scenario,
        challenge_id,
        admissible,
        challenged_payload,
    )

    with direct_vm.expect_revert(
        "Resolution version must differ from challenged version"
    ):
        contract.review_open_challenge_resolution(
            challenge_id,
            resolution_url(
                scenario
            ),
            "counter-v1",
            digest(
                valid_payload
            ),
        )

    with direct_vm.expect_revert(
        "Resolution digest must differ from challenged digest"
    ):
        contract.review_open_challenge_resolution(
            challenge_id,
            resolution_url(
                scenario
            ),
            "resolution-v2",
            digest(
                challenged_payload
            ),
        )

    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )


def test_open_challenged_bundle_can_still_be_superseded(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        scenario,
        _admissible,
        challenge_id,
        _material_review,
        _challenged_payload,
    ) = open_material_challenge(
        contract,
        direct_vm,
    )

    new_bundle = (
        contract.create_superseding_bundle(
            scenario["bundle"]
        )
    )

    assert (
        new_bundle
        > scenario["bundle"]
    )

    assert (
        contract.get_bundle_superseded_by(
            scenario["bundle"]
        )
        == new_bundle
    )

    # Historical challenge remains intact rather than being erased.
    assert (
        contract.get_open_challenge_id(
            scenario["bundle"]
        )
        == challenge_id
    )
