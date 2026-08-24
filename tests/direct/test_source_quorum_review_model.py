from pathlib import Path

import pytest


def deploy_contract(
    direct_vm,
    direct_deploy,
):
    direct_vm.check_pickling = True

    return direct_deploy(
        "contracts/source_quorum.py",
        3600,
    )


def test_review_ledger_starts_empty(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    authority = contract.create_authority(
        "Primary",
        "PRIMARY_GROUP",
        0,
    )

    contract.add_authority_origin(
        authority,
        1,
        "https://primary.example",
    )

    contract.seal_authority_revision(
        authority,
        1,
    )

    corroborator = contract.create_authority(
        "Corroborator",
        "CORROBORATOR_GROUP",
        0,
    )

    contract.add_authority_origin(
        corroborator,
        1,
        "https://corroborator.example",
    )

    contract.seal_authority_revision(
        corroborator,
        1,
    )

    policy = contract.create_policy(
        "Review Test Policy",
        1,
        86400,
        "TEST_FACT",
    )

    contract.add_policy_authority(
        policy,
        1,
        authority,
        1,
        "primary",
    )

    contract.add_policy_authority(
        policy,
        1,
        corroborator,
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
        "Test claim",
    )

    assert contract.get_bundle_review_count(
        bundle
    ) == 0

    assert contract.get_latest_review_id(
        bundle
    ) == 0

    with direct_vm.expect_revert(
        "Review does not exist"
    ):
        contract.get_review_status(1)


def test_review_storage_has_no_public_bypass_writer():
    source = Path(
        "contracts/source_quorum.py"
    ).read_text()

    forbidden = (
        "def record_review(",
        "def set_review_status(",
        "def set_review_result(",
        "def force_review(",
        "def admin_review(",
    )

    for signature in forbidden:
        assert signature not in source

    # No ordinary request path is allowed to manufacture
    # consequential challenge state.
    request_start = source.index(
        "def submit_challenge_request("
    )
    request_end = source.index(
        "def expire_challenge_request("
    )

    request_body = source[
        request_start:request_end
    ]

    assert (
        "self.bundle_open_challenge_id["
        not in request_body
    )
