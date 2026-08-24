import hashlib
import json
import re
import time


def deploy_contract(
    direct_vm,
    direct_deploy,
):
    direct_vm.check_pickling = True

    return direct_deploy(
        "contracts/source_quorum.py",
        3600,
    )


def evidence_body(
    version,
    published_at,
    fact_code,
):
    return json.dumps(
        {
            "version_reference": version,
            "published_at": published_at,
            "fact_code": fact_code,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_for(body):
    return (
        "sha256:"
        + hashlib.sha256(
            body.encode("utf-8")
        ).hexdigest()
    )


def create_authority(
    contract,
    number,
):
    authority_id = contract.create_authority(
        f"Authority {number}",
        f"GROUP_{number}",
        0,
    )

    origin = (
        f"https://authority-{number}.example"
    )

    contract.add_authority_origin(
        authority_id,
        1,
        origin,
    )

    contract.seal_authority_revision(
        authority_id,
        1,
    )

    return authority_id, origin


def build_bundle(
    contract,
):
    published_at = int(
        time.time()
    ) - 30

    primary, primary_origin = (
        create_authority(
            contract,
            1,
        )
    )

    corroborator_a, origin_a = (
        create_authority(
            contract,
            2,
        )
    )

    corroborator_b, origin_b = (
        create_authority(
            contract,
            3,
        )
    )

    policy = contract.create_policy(
        "Structured Evidence Policy",
        2,
        86400,
        "EVENT_RESULT",
    )

    contract.add_policy_authority(
        policy,
        1,
        primary,
        1,
        "primary",
    )

    contract.add_policy_authority(
        policy,
        1,
        corroborator_a,
        1,
        "corroborator",
    )

    contract.add_policy_authority(
        policy,
        1,
        corroborator_b,
        1,
        "corroborator",
    )

    contract.activate_policy(
        policy,
        1,
    )

    bundle = contract.create_bundle(
        policy,
        1,
        "The event result is YES",
    )

    locations = {
        "primary":
            primary_origin + "/record/v1",
        "a":
            origin_a + "/record/v1",
        "b":
            origin_b + "/record/v1",
    }

    bodies = {
        "primary": evidence_body(
            "v1",
            published_at,
            "YES",
        ),
        "a": evidence_body(
            "v1",
            published_at,
            "YES",
        ),
        "b": evidence_body(
            "v1",
            published_at,
            "YES",
        ),
    }

    contract.add_evidence_record(
        bundle,
        primary,
        1,
        primary_origin,
        locations["primary"],
        "v1",
        digest_for(
            bodies["primary"]
        ),
        published_at,
        True,
    )

    contract.add_evidence_record(
        bundle,
        corroborator_a,
        1,
        origin_a,
        locations["a"],
        "v1",
        digest_for(
            bodies["a"]
        ),
        published_at,
        False,
    )

    contract.add_evidence_record(
        bundle,
        corroborator_b,
        1,
        origin_b,
        locations["b"],
        "v1",
        digest_for(
            bodies["b"]
        ),
        published_at,
        False,
    )

    contract.freeze_bundle(
        bundle
    )

    return {
        "bundle": bundle,
        "published_at": published_at,
        "locations": locations,
        "bodies": bodies,
    }


def mock_all(
    direct_vm,
    scenario,
    overrides=None,
):
    overrides = overrides or {}

    for name in (
        "primary",
        "a",
        "b",
    ):
        body = overrides.get(
            name,
            scenario["bodies"][name],
        )

        direct_vm.mock_web(
            re.escape(
                scenario[
                    "locations"
                ][name]
            ),
            {
                "status": 200,
                "body": body,
            },
        )


def test_structured_review_agrees_but_fails_closed_before_semantic_independence(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    review_id = (
        contract.review_frozen_bundle(
            scenario["bundle"]
        )
    )

    assert review_id == 1

    assert (
        contract.get_review_status(
            review_id
        )
        == "INADMISSIBLE"
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "SEMANTIC_INDEPENDENCE_UNVERIFIED"
    )

    # Structural diversity alone is NOT semantic independence.
    #
    # Until the semantic/provenance validator layer exists, the
    # consequential independence fields must remain fail-closed.
    assert (
        contract.
        get_review_independent_corroborator_count(
            review_id
        )
        == 0
    )

    assert (
        contract.
        get_review_qualifying_authority_set(
            review_id
        )
        == ""
    )

    assert (
        contract.
        get_review_excluded_authority_set(
            review_id
        )
        == ""
    )

    assert not (
        contract.
        get_review_conflict_detected(
            review_id
        )
    )

    # Validator independently fetches the same evidence.
    assert direct_vm.run_validator() is True


def test_validator_rejects_changed_primary_version(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    contract.review_frozen_bundle(
        scenario["bundle"]
    )

    direct_vm.clear_mocks()

    changed_primary = evidence_body(
        "v2",
        scenario["published_at"],
        "YES",
    )

    mock_all(
        direct_vm,
        scenario,
        {
            "primary": changed_primary,
        },
    )

    assert direct_vm.run_validator() is False


def test_validator_rejects_changed_publication_timestamp(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    contract.review_frozen_bundle(
        scenario["bundle"]
    )

    direct_vm.clear_mocks()

    changed = evidence_body(
        "v1",
        scenario["published_at"] - 1,
        "YES",
    )

    mock_all(
        direct_vm,
        scenario,
        {
            "a": changed,
        },
    )

    assert direct_vm.run_validator() is False


def test_validator_rejects_changed_fact(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    contract.review_frozen_bundle(
        scenario["bundle"]
    )

    direct_vm.clear_mocks()

    changed = evidence_body(
        "v1",
        scenario["published_at"],
        "NO",
    )

    mock_all(
        direct_vm,
        scenario,
        {
            "b": changed,
        },
    )

    assert direct_vm.run_validator() is False


def test_validator_rejects_changed_fetched_bytes(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    contract.review_frozen_bundle(
        scenario["bundle"]
    )

    direct_vm.clear_mocks()

    # Same semantic fields, different immutable bytes.
    changed = json.dumps(
        {
            "version_reference": "v1",
            "published_at":
                scenario["published_at"],
            "fact_code": "YES",
        },
        indent=2,
        sort_keys=True,
    )

    mock_all(
        direct_vm,
        scenario,
        {
            "a": changed,
        },
    )

    assert direct_vm.run_validator() is False


def test_validator_rejects_unavailable_corroborator(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    contract.review_frozen_bundle(
        scenario["bundle"]
    )

    direct_vm.clear_mocks()

    direct_vm.mock_web(
        re.escape(
            scenario["locations"][
                "primary"
            ]
        ),
        {
            "status": 200,
            "body":
                scenario["bodies"][
                    "primary"
                ],
        },
    )

    direct_vm.mock_web(
        re.escape(
            scenario["locations"]["a"]
        ),
        {
            "status": 503,
            "body": "",
        },
    )

    direct_vm.mock_web(
        re.escape(
            scenario["locations"]["b"]
        ),
        {
            "status": 200,
            "body":
                scenario["bodies"]["b"],
        },
    )

    assert direct_vm.run_validator() is False


def test_structured_reviews_are_append_only(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    mock_all(
        direct_vm,
        scenario,
    )

    first_review = (
        contract.review_frozen_bundle(
            scenario["bundle"]
        )
    )

    assert first_review == 1

    assert (
        contract.get_review_attempt_number(
            first_review
        )
        == 1
    )

    assert (
        contract.get_review_previous_id(
            first_review
        )
        == 0
    )

    first_status = (
        contract.get_review_status(
            first_review
        )
    )

    direct_vm.clear_mocks()

    mock_all(
        direct_vm,
        scenario,
    )

    second_review = (
        contract.review_frozen_bundle(
            scenario["bundle"]
        )
    )

    assert second_review == 2

    assert (
        contract.get_bundle_review_count(
            scenario["bundle"]
        )
        == 2
    )

    assert (
        contract.get_latest_review_id(
            scenario["bundle"]
        )
        == second_review
    )

    assert (
        contract.get_review_attempt_number(
            second_review
        )
        == 2
    )

    assert (
        contract.get_review_previous_id(
            second_review
        )
        == first_review
    )

    # Earlier history remains unchanged and readable.
    assert (
        contract.get_review_status(
            first_review
        )
        == first_status
    )


def test_leader_unavailability_is_transient_not_inadmissible(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    scenario = build_bundle(
        contract
    )

    direct_vm.mock_web(
        re.escape(
            scenario["locations"][
                "primary"
            ]
        ),
        {
            "status": 200,
            "body":
                scenario["bodies"][
                    "primary"
                ],
        },
    )

    direct_vm.mock_web(
        re.escape(
            scenario["locations"]["a"]
        ),
        {
            "status": 503,
            "body": "",
        },
    )

    direct_vm.mock_web(
        re.escape(
            scenario["locations"]["b"]
        ),
        {
            "status": 200,
            "body":
                scenario["bodies"]["b"],
        },
    )

    review_id = (
        contract.review_frozen_bundle(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_review_status(
            review_id
        )
        == "UNAVAILABLE"
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "EVIDENCE_UNAVAILABLE"
    )

    # Transient failure is not converted into substantive rejection.
    assert (
        contract.get_review_status(
            review_id
        )
        != "INADMISSIBLE"
    )

    assert (
        contract.
        get_review_independent_corroborator_count(
            review_id
        )
        == 0
    )
