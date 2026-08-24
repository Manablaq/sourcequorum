def deploy_contract(
    direct_vm,
    direct_deploy,
):
    direct_vm.check_pickling = True

    return direct_deploy(
        "contracts/source_quorum.py",
        3600,
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

    contract.add_authority_origin(
        authority_id,
        1,
        f"https://authority-{number}.example",
    )

    contract.seal_authority_revision(
        authority_id,
        1,
    )

    return authority_id


def test_bundle_record_index_preserves_insertion_order(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    primary = create_authority(
        contract,
        1,
    )

    corroborator = create_authority(
        contract,
        2,
    )

    policy = contract.create_policy(
        "Indexed Policy",
        1,
        86400,
        "TEST_FACT",
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
        "Indexed evidence claim",
    )

    primary_record = contract.add_evidence_record(
        bundle,
        primary,
        1,
        "https://authority-1.example",
        "https://authority-1.example/record/v1",
        "v1",
        "sha256:primary",
        1,
        True,
    )

    corroborator_record = contract.add_evidence_record(
        bundle,
        corroborator,
        1,
        "https://authority-2.example",
        "https://authority-2.example/record/v1",
        "v1",
        "sha256:corroborator",
        1,
        False,
    )

    assert contract.get_bundle_record_id(
        bundle,
        1,
    ) == primary_record

    assert contract.get_bundle_record_id(
        bundle,
        2,
    ) == corroborator_record

    assert contract.get_max_bundle_evidence_records() == 16

    with direct_vm.expect_revert(
        "record_index exceeds bundle record count"
    ):
        contract.get_bundle_record_id(
            bundle,
            3,
        )


def test_impossible_policy_quorum_is_rejected(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    with direct_vm.expect_revert(
        "minimum_independent_corroborators exceeds bundle limit"
    ):
        contract.create_policy(
            "Impossible Policy",
            16,
            86400,
            "TEST_FACT",
        )
