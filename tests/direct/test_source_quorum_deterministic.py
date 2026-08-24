def deploy_contract(direct_vm, direct_deploy):
    direct_vm.check_pickling = True

    return direct_deploy(
        "contracts/source_quorum.py",
        3600,
    )


def create_authority(
    contract,
    name,
    group,
    origin,
):
    authority_id = contract.create_authority(
        name,
        group,
        0,
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

    return authority_id


def create_active_policy(contract):
    primary = create_authority(
        contract,
        "Primary Authority",
        "GROUP_PRIMARY",
        "https://primary.example",
    )

    corroborator_a = create_authority(
        contract,
        "Corroborator A",
        "GROUP_A",
        "https://a.example",
    )

    corroborator_b = create_authority(
        contract,
        "Corroborator B",
        "GROUP_B",
        "https://b.example",
    )

    policy_id = contract.create_policy(
        "Flight Status Policy",
        2,
        86400,
        "FLIGHT_STATUS",
    )

    contract.add_policy_authority(
        policy_id,
        1,
        primary,
        1,
        "primary",
    )

    contract.add_policy_authority(
        policy_id,
        1,
        corroborator_a,
        1,
        "corroborator",
    )

    contract.add_policy_authority(
        policy_id,
        1,
        corroborator_b,
        1,
        "corroborator",
    )

    contract.activate_policy(
        policy_id,
        1,
    )

    return (
        policy_id,
        primary,
        corroborator_a,
        corroborator_b,
    )


def add_bundle_records(
    contract,
    bundle_id,
    primary,
    corroborator_a,
    corroborator_b,
):
    primary_record = contract.add_evidence_record(
        bundle_id,
        primary,
        1,
        "https://primary.example",
        "https://primary.example/records/42",
        "primary-v1",
        "sha256:primary",
        1,
        True,
    )

    contract.add_evidence_record(
        bundle_id,
        corroborator_a,
        1,
        "https://a.example",
        "https://a.example/records/42",
        "a-v1",
        "sha256:a",
        1,
        False,
    )

    contract.add_evidence_record(
        bundle_id,
        corroborator_b,
        1,
        "https://b.example",
        "https://b.example/records/42",
        "b-v1",
        "sha256:b",
        1,
        False,
    )

    return primary_record


def test_owner_access_control(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert("Only owner"):
            contract.create_authority(
                "Bad Authority",
                "GROUP_BAD",
                0,
            )

        with direct_vm.expect_revert("Only owner"):
            contract.create_policy(
                "Bad Policy",
                1,
                3600,
                "TEST",
            )


def test_authority_revision_is_immutable_after_sealing(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    authority_id = create_authority(
        contract,
        "Authority A",
        "GROUP_A",
        "https://authority.example",
    )

    assert authority_id == 1
    assert contract.is_authority_sealed(
        authority_id,
        1,
    )

    assert contract.get_authority_origin(
        authority_id,
        1,
        1,
    ) == "https://authority.example"

    with direct_vm.expect_revert(
        "Authority revision is sealed"
    ):
        contract.add_authority_origin(
            authority_id,
            1,
            "https://replacement.example",
        )

    revision_2 = contract.create_authority_revision(
        authority_id,
        "Authority A V2",
        "GROUP_A",
        0,
    )

    assert revision_2 == 2

    assert contract.get_latest_authority_revision(
        authority_id
    ) == 2

    assert contract.is_authority_sealed(
        authority_id,
        1,
    )

    assert not contract.is_authority_sealed(
        authority_id,
        2,
    )


def test_duplicate_independence_group_cannot_fake_quorum(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    primary = create_authority(
        contract,
        "Primary",
        "PRIMARY",
        "https://primary.example",
    )

    a = create_authority(
        contract,
        "Outlet A",
        "SHARED_GROUP",
        "https://a.example",
    )

    b = create_authority(
        contract,
        "Outlet B",
        "SHARED_GROUP",
        "https://b.example",
    )

    policy_id = contract.create_policy(
        "Policy",
        1,
        86400,
        "FACT",
    )

    contract.add_policy_authority(
        policy_id,
        1,
        primary,
        1,
        "primary",
    )

    contract.add_policy_authority(
        policy_id,
        1,
        a,
        1,
        "corroborator",
    )

    with direct_vm.expect_revert(
        "Independence group already used in policy"
    ):
        contract.add_policy_authority(
            policy_id,
            1,
            b,
            1,
            "corroborator",
        )


def test_activated_policy_is_not_rewritten(
    direct_vm,
    direct_deploy,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        _,
        _,
    ) = create_active_policy(contract)

    assert contract.is_policy_sealed(
        policy_id,
        1,
    )

    assert contract.is_policy_active(
        policy_id,
        1,
    )

    with direct_vm.expect_revert(
        "Policy version is sealed"
    ):
        contract.add_policy_authority(
            policy_id,
            1,
            primary,
            1,
            "primary",
        )

    revision_2 = contract.create_policy_revision(
        policy_id,
        "Flight Status Policy V2",
        1,
        43200,
        "FLIGHT_STATUS",
    )

    assert revision_2 == 2
    assert contract.get_latest_policy_version(
        policy_id
    ) == 2

    # Historical V1 remains intact.
    assert contract.is_policy_sealed(
        policy_id,
        1,
    )

    assert contract.is_policy_active(
        policy_id,
        1,
    )

    # V2 is a separate definition.
    assert not contract.is_policy_sealed(
        policy_id,
        2,
    )


def test_unapproved_and_lookalike_sources_are_rejected(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        _,
        _,
    ) = create_active_policy(contract)

    unapproved = create_authority(
        contract,
        "Unapproved",
        "UNAPPROVED",
        "https://unapproved.example",
    )

    with direct_vm.prank(direct_alice):
        bundle_id = contract.create_bundle(
            policy_id,
            1,
            "Flight SQ42 was cancelled",
        )

        with direct_vm.expect_revert(
            "Authority revision is not approved for this policy role"
        ):
            contract.add_evidence_record(
                bundle_id,
                unapproved,
                1,
                "https://unapproved.example",
                "https://unapproved.example/report",
                "v1",
                "sha256:x",
                1,
                False,
            )

        with direct_vm.expect_revert(
            "Evidence location does not match approved origin"
        ):
            contract.add_evidence_record(
                bundle_id,
                primary,
                1,
                "https://primary.example",
                "https://primary.example.evil.test/report",
                "v1",
                "sha256:x",
                1,
                True,
            )


def test_frozen_bundle_is_immutable(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        corroborator_a,
        corroborator_b,
    ) = create_active_policy(contract)

    with direct_vm.prank(direct_alice):
        bundle_id = contract.create_bundle(
            policy_id,
            1,
            "Flight SQ42 was cancelled",
        )

        primary_record = add_bundle_records(
            contract,
            bundle_id,
            primary,
            corroborator_a,
            corroborator_b,
        )

        assert contract.get_bundle_record_count(
            bundle_id
        ) == 3

        assert contract.get_bundle_corroborator_count(
            bundle_id
        ) == 2

        assert contract.get_bundle_primary_record_id(
            bundle_id
        ) == primary_record

        contract.freeze_bundle(bundle_id)

        assert contract.is_bundle_frozen(
            bundle_id
        )

        with direct_vm.expect_revert(
            "Bundle is frozen"
        ):
            contract.add_evidence_record(
                bundle_id,
                corroborator_a,
                1,
                "https://a.example",
                "https://a.example/other",
                "v2",
                "sha256:other",
                1,
                False,
            )


def test_new_evidence_supersedes_instead_of_mutating_history(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        corroborator_a,
        corroborator_b,
    ) = create_active_policy(contract)

    with direct_vm.prank(direct_alice):
        old_bundle = contract.create_bundle(
            policy_id,
            1,
            "Flight SQ42 was cancelled",
        )

        add_bundle_records(
            contract,
            old_bundle,
            primary,
            corroborator_a,
            corroborator_b,
        )

        contract.freeze_bundle(old_bundle)

        new_bundle = contract.create_superseding_bundle(
            old_bundle
        )

        assert new_bundle != old_bundle

        assert contract.get_bundle_superseded_by(
            old_bundle
        ) == new_bundle

        assert contract.get_bundle_supersedes(
            new_bundle
        ) == old_bundle

        assert contract.is_bundle_frozen(
            old_bundle
        )

        assert not contract.is_bundle_frozen(
            new_bundle
        )

        # Exact historical policy binding survives.
        assert contract.get_bundle_policy_id(
            new_bundle
        ) == policy_id

        assert contract.get_bundle_policy_version(
            new_bundle
        ) == 1

        with direct_vm.expect_revert(
            "Bundle already has a superseding bundle"
        ):
            contract.create_superseding_bundle(
                old_bundle
            )


def test_challenge_request_is_not_consequential_before_review(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        corroborator_a,
        corroborator_b,
    ) = create_active_policy(contract)

    with direct_vm.prank(direct_alice):
        bundle_id = contract.create_bundle(
            policy_id,
            1,
            "Flight SQ42 was cancelled",
        )

        add_bundle_records(
            contract,
            bundle_id,
            primary,
            corroborator_a,
            corroborator_b,
        )

        contract.freeze_bundle(bundle_id)

    with direct_vm.prank(direct_bob):
        # A digest is required even though this is still only
        # untrusted submitted counter-evidence.
        with direct_vm.expect_revert(
            "Challenge request requires evidence digest"
        ):
            contract.submit_challenge_request(
                bundle_id,
                "https://counter.example/record/42",
                "",
                "Counter-evidence exists",
            )

        challenge_id = contract.submit_challenge_request(
            bundle_id,
            "https://counter.example/record/42",
            "sha256:counter-evidence",
            "Counter-evidence may contradict the bundle",
        )

        assert challenge_id > 0

        assert contract.bundle_has_pending_challenge_request(
            bundle_id
        )

        assert contract.get_pending_challenge_id(
            bundle_id
        ) == challenge_id

        # CRITICAL:
        # mere user submission has no consequential effect.
        assert not contract.bundle_has_open_challenge(
            bundle_id
        )

        assert contract.get_open_challenge_id(
            bundle_id
        ) == 0

        with direct_vm.expect_revert(
            "Bundle already has a pending challenge request"
        ):
            contract.submit_challenge_request(
                bundle_id,
                "https://another.example/record/99",
                "sha256:second",
                "Another allegation",
            )

        # Liveness exists, but no caller can discard the request early.
        with direct_vm.expect_revert(
            "Challenge request deadline not reached"
        ):
            contract.expire_challenge_request(
                challenge_id
            )

        assert not contract.is_challenge_request_expired(
            challenge_id
        )


def test_superseded_bundle_cannot_receive_new_challenge_request(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = deploy_contract(
        direct_vm,
        direct_deploy,
    )

    (
        policy_id,
        primary,
        corroborator_a,
        corroborator_b,
    ) = create_active_policy(contract)

    with direct_vm.prank(direct_alice):
        old_bundle = contract.create_bundle(
            policy_id,
            1,
            "Flight SQ42 was cancelled",
        )

        add_bundle_records(
            contract,
            old_bundle,
            primary,
            corroborator_a,
            corroborator_b,
        )

        contract.freeze_bundle(old_bundle)

        new_bundle = contract.create_superseding_bundle(
            old_bundle
        )

        assert new_bundle > old_bundle

    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert(
            "Superseded bundle cannot receive challenge request"
        ):
            contract.submit_challenge_request(
                old_bundle,
                "https://counter.example/old-record",
                "sha256:old-counter",
                "Old bundle allegation",
            )
