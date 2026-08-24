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


def body(
    version,
    published_at,
    fact,
    content,
    provenance,
):
    return json.dumps(
        {
            "version_reference": version,
            "published_at": published_at,
            "fact_code": fact,
            "content": content,
            "provenance": provenance,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value):
    return (
        "sha256:"
        + hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()
    )


def authority(
    contract,
    number,
):
    aid = contract.create_authority(
        f"Authority {number}",
        f"GROUP_{number}",
        0,
    )

    origin = (
        f"https://semantic-{number}.example"
    )

    contract.add_authority_origin(
        aid,
        1,
        origin,
    )

    contract.seal_authority_revision(
        aid,
        1,
    )

    return aid, origin


def build_scenario(contract):
    published_at = int(
        time.time()
    ) - 30

    primary, primary_origin = authority(
        contract,
        1,
    )

    a, origin_a = authority(
        contract,
        2,
    )

    b, origin_b = authority(
        contract,
        3,
    )

    policy = contract.create_policy(
        "Semantic Provenance Policy",
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
        a,
        1,
        "corroborator",
    )

    contract.add_policy_authority(
        policy,
        1,
        b,
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
        "Event result is YES",
    )

    locations = {
        "primary":
            primary_origin + "/v1",
        "a":
            origin_a + "/v1",
        "b":
            origin_b + "/v1",
    }

    bodies = {
        "primary": body(
            "v1",
            published_at,
            "YES",
            "Primary authority reports YES.",
            "First-party official record.",
        ),
        "a": body(
            "v1",
            published_at,
            "YES",
            "Authority 2 independently reports YES.",
            "Independent first-party observation.",
        ),
        "b": body(
            "v1",
            published_at,
            "YES",
            "Authority 3 independently reports YES.",
            "Independent first-party observation.",
        ),
    }

    contract.add_evidence_record(
        bundle,
        primary,
        1,
        primary_origin,
        locations["primary"],
        "v1",
        digest(bodies["primary"]),
        published_at,
        True,
    )

    contract.add_evidence_record(
        bundle,
        a,
        1,
        origin_a,
        locations["a"],
        "v1",
        digest(bodies["a"]),
        published_at,
        False,
    )

    contract.add_evidence_record(
        bundle,
        b,
        1,
        origin_b,
        locations["b"],
        "v1",
        digest(bodies["b"]),
        published_at,
        False,
    )

    contract.freeze_bundle(bundle)

    return {
        "bundle": bundle,
        "locations": locations,
        "bodies": bodies,
    }


def mock_web(direct_vm, scenario):
    for name in (
        "primary",
        "a",
        "b",
    ):
        direct_vm.mock_web(
            re.escape(
                scenario[
                    "locations"
                ][name]
            ),
            {
                "status": 200,
                "body":
                    scenario[
                        "bodies"
                    ][name],
            },
        )


def mock_semantic(
    direct_vm,
    relation_a="INDEPENDENT",
    relation_b="INDEPENDENT",
    conflict_a=False,
    conflict_b=False,
    upstream_a=(1, 1),
    upstream_b=(1, 1),
):
    def classification(
        authority_id,
        relationship,
        conflict,
        upstream,
    ):
        if relationship == "INDEPENDENT":
            basis_code = (
                "FIRST_PARTY_ORIGINAL"
            )
            upstream_id = 0
            upstream_revision = 0

        elif relationship == "DERIVED":
            basis_code = (
                "DERIVED_FROM_AUTHORITY"
            )
            upstream_id = upstream[0]
            upstream_revision = upstream[1]

        else:
            basis_code = (
                "PROVENANCE_UNVERIFIED"
            )
            upstream_id = 0
            upstream_revision = 0

        return {
            "authority_id":
                authority_id,
            "authority_revision": 1,
            "relationship":
                relationship,
            "basis_code":
                basis_code,
            "upstream_authority_id":
                upstream_id,
            "upstream_authority_revision":
                upstream_revision,
            "material_conflict":
                conflict,
        }

    result = {
        "classifications": [
            classification(
                2,
                relation_a,
                conflict_a,
                upstream_a,
            ),
            classification(
                3,
                relation_b,
                conflict_b,
                upstream_b,
            ),
        ]
    }

    direct_vm.mock_llm(
        r"(?s).*SourceQuorum semantic provenance review.*",
        json.dumps(result),
    )

def create_structured_review(
    contract,
    direct_vm,
    scenario,
):
    mock_web(
        direct_vm,
        scenario,
    )

    review_id = (
        contract.review_frozen_bundle(
            scenario["bundle"]
        )
    )

    assert (
        contract.get_review_reason_code(
            review_id
        )
        == "SEMANTIC_INDEPENDENCE_UNVERIFIED"
    )

    direct_vm.clear_mocks()

    return review_id


def test_independent_semantic_quorum_can_be_admissible(
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

    assert (
        contract.get_review_reason_code(
            semantic
        )
        == "SEMANTIC_INDEPENDENCE_CONFIRMED"
    )

    assert (
        contract.
        get_review_independent_corroborator_count(
            semantic
        )
        == 2
    )

    assert (
        contract.
        get_review_qualifying_authority_set(
            semantic
        )
        == "2:1|3:1"
    )

    assert (
        contract.get_review_previous_id(
            semantic
        )
        == structured
    )

    assert direct_vm.run_validator() is True


def test_derived_source_does_not_count_toward_quorum(
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

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
        relation_b="DERIVED",
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
        == "INSUFFICIENT_CORROBORATION"
    )

    assert (
        contract.
        get_review_independent_corroborator_count(
            semantic
        )
        == 1
    )

    assert (
        contract.
        get_review_qualifying_authority_set(
            semantic
        )
        == "2:1"
    )

    assert (
        contract.
        get_review_excluded_authority_set(
            semantic
        )
        == "3:1"
    )


def test_validator_rejects_different_semantic_classification(
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

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
    )

    contract.review_semantic_independence(
        structured
    )

    direct_vm.clear_mocks()

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
        relation_b="DERIVED",
    )

    assert direct_vm.run_validator() is False


def test_only_latest_structured_review_can_be_completed(
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

    first = create_structured_review(
        contract,
        direct_vm,
        scenario,
    )

    second = create_structured_review(
        contract,
        direct_vm,
        scenario,
    )

    assert second > first

    with direct_vm.expect_revert(
        "Structured review is not latest"
    ):
        contract.review_semantic_independence(
            first
        )


def test_validator_rejects_different_derived_upstream_identity(
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

    mock_web(
        direct_vm,
        scenario,
    )

    mock_semantic(
        direct_vm,
        relation_b="DERIVED",
        upstream_b=(1, 1),
    )

    semantic = (
        contract.
        review_semantic_independence(
            structured
        )
    )

    stored = json.loads(
        contract.
        get_review_evidence_facts_canonical(
            semantic
        )
    )

    semantic_items = (
        stored["semantic"][
            "classifications"
        ]
    )

    assert (
        semantic_items[1][
            "upstream_authority_id"
        ]
        == 1
    )

    assert (
        semantic_items[1][
            "upstream_authority_revision"
        ]
        == 1
    )

    direct_vm.clear_mocks()

    mock_web(
        direct_vm,
        scenario,
    )

    # Same DERIVED relationship and same final quorum consequence,
    # but a different exact provenance claim.
    mock_semantic(
        direct_vm,
        relation_b="DERIVED",
        upstream_b=(2, 1),
    )

    assert direct_vm.run_validator() is False


def test_classifier_cannot_use_self_as_derived_upstream(
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

    mock_web(
        direct_vm,
        scenario,
    )

    # Authority 3 cannot claim authority 3:1 as its own upstream.
    mock_semantic(
        direct_vm,
        relation_b="DERIVED",
        upstream_b=(3, 1),
    )

    with direct_vm.expect_revert(
        "Derived provenance fields are inconsistent"
    ):
        contract.review_semantic_independence(
            structured
        )
