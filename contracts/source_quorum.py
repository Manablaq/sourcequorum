# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
from datetime import datetime, timezone


ROLE_PRIMARY = "primary"
ROLE_CORROBORATOR = "corroborator"

REVIEW_KIND_EVIDENCE = "evidence"
REVIEW_KIND_CHALLENGE = "challenge"

REVIEW_ADMISSIBLE = "ADMISSIBLE"
REVIEW_INADMISSIBLE = "INADMISSIBLE"
REVIEW_STALE = "STALE"
REVIEW_CONFLICTED = "CONFLICTED"
REVIEW_INSUFFICIENT_CORROBORATION = "INSUFFICIENT_CORROBORATION"
REVIEW_UNAVAILABLE = "UNAVAILABLE"

# SourceQuorum v1 protocol bound.
#
# This is not a GenLayer platform limit. It bounds the number of
# external evidence fetches and semantic reviews required per bundle.
MAX_BUNDLE_EVIDENCE_RECORDS = 16


@allow_storage
@dataclass
class AuthorityRevision:
    authority_id: u256
    revision: u256
    name: str
    independence_group: str
    valid_from: u256
    valid_until: u256
    sealed: bool


@allow_storage
@dataclass
class PolicyVersion:
    policy_id: u256
    version: u256
    name: str
    minimum_independent_corroborators: u256
    maximum_evidence_age: u256
    fact_namespace: str
    sealed: bool


@allow_storage
@dataclass
class EvidenceBundle:
    bundle_id: u256
    policy_id: u256
    policy_version: u256
    claim: str
    fact_namespace: str
    submitted_by: Address
    submitted_at: u256
    supersedes_bundle_id: u256
    primary_record_id: u256
    record_count: u256
    corroborator_count: u256
    frozen: bool


@allow_storage
@dataclass
class EvidenceRecord:
    record_id: u256
    bundle_id: u256
    authority_id: u256
    authority_revision: u256
    retrieval_origin: str
    retrieval_location: str
    version_reference: str
    submitted_digest: str
    claimed_published_at: u256
    submitted_at: u256
    is_primary: bool


@allow_storage
@dataclass
class ChallengeRequest:
    challenge_id: u256
    bundle_id: u256
    submitted_by: Address
    evidence_reference: str
    evidence_digest: str
    reason: str
    submitted_at: u256
    deadline: u256
    expired: bool



@allow_storage
@dataclass
class ReviewRecord:
    review_id: u256
    bundle_id: u256
    attempt_number: u256
    previous_review_id: u256

    review_kind: str
    challenge_request_id: u256

    policy_id: u256
    policy_version: u256

    reviewed_at: u256
    status: str
    fact_code: str

    primary_record_id: u256
    verified_primary_version: str
    verified_primary_published_at: u256

    qualifying_authority_set: str
    excluded_authority_set: str
    evidence_facts_canonical: str

    independent_corroborator_count: u256
    conflict_detected: bool
    reason_code: str


class SourceQuorum(gl.Contract):
    owner: Address
    challenge_window_seconds: u256

    next_authority_id: u256
    next_policy_id: u256
    next_bundle_id: u256
    next_record_id: u256
    next_challenge_id: u256
    next_review_id: u256

    authority_exists: TreeMap[str, bool]
    authority_latest_revision: TreeMap[str, u256]
    authorities: TreeMap[str, AuthorityRevision]
    authority_origin_count: TreeMap[str, u256]
    authority_origins: TreeMap[str, str]
    authority_origin_membership: TreeMap[str, bool]
    authority_revoked_at: TreeMap[str, u256]

    policy_exists: TreeMap[str, bool]
    policy_latest_version: TreeMap[str, u256]
    policies: TreeMap[str, PolicyVersion]
    policy_activated_at: TreeMap[str, u256]
    policy_primary_count: TreeMap[str, u256]
    policy_corroborator_count: TreeMap[str, u256]
    policy_authority_membership: TreeMap[str, bool]
    policy_independence_group_used: TreeMap[str, bool]

    bundle_exists: TreeMap[str, bool]
    bundles: TreeMap[str, EvidenceBundle]
    bundle_authority_used: TreeMap[str, bool]

    # 1-based immutable record index for bounded review enumeration.
    bundle_record_ids: TreeMap[str, u256]
    bundle_superseded_by: TreeMap[str, u256]

    record_exists: TreeMap[str, bool]
    records: TreeMap[str, EvidenceRecord]

    challenge_exists: TreeMap[str, bool]
    challenges: TreeMap[str, ChallengeRequest]

    # A submitted challenge request is deliberately non-consequential.
    # It must later pass validator-backed materiality review before
    # bundle_open_challenge_id can ever be set.
    bundle_pending_challenge_id: TreeMap[str, u256]
    bundle_open_challenge_id: TreeMap[str, u256]

    # Append-only review ledger.
    review_exists: TreeMap[str, bool]
    reviews: TreeMap[str, ReviewRecord]

    bundle_review_count: TreeMap[str, u256]
    bundle_latest_review_id: TreeMap[str, u256]

    def __init__(self, challenge_window_seconds: int):
        if challenge_window_seconds <= 0:
            raise gl.vm.UserError("Challenge window must be positive")

        self.owner = gl.message.sender_address
        self.challenge_window_seconds = u256(challenge_window_seconds)

        self.next_authority_id = u256(1)
        self.next_policy_id = u256(1)
        self.next_bundle_id = u256(1)
        self.next_record_id = u256(1)
        self.next_challenge_id = u256(1)
        self.next_review_id = u256(1)

    # ------------------------------------------------------------------
    # Internal deterministic helpers
    # ------------------------------------------------------------------

    def _now(self) -> u256:
        return u256(int(datetime.now(timezone.utc).timestamp()))

    def _only_owner(self) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError("Only owner")

    def _id(self, value: int, label: str) -> u256:
        if value <= 0:
            raise gl.vm.UserError(f"{label} must be positive")
        return u256(value)

    def _authority_id_key(self, authority_id: u256) -> str:
        return str(authority_id)

    def _authority_key(self, authority_id: u256, revision: u256) -> str:
        return f"{authority_id}:{revision}"

    def _policy_id_key(self, policy_id: u256) -> str:
        return str(policy_id)

    def _policy_key(self, policy_id: u256, version: u256) -> str:
        return f"{policy_id}:{version}"

    def _bundle_key(self, bundle_id: u256) -> str:
        return str(bundle_id)

    def _record_key(self, record_id: u256) -> str:
        return str(record_id)

    def _challenge_key(self, challenge_id: u256) -> str:
        return str(challenge_id)

    def _normalize_origin(self, origin: str) -> str:
        normalized = origin.strip().rstrip("/")

        if len(normalized) <= len("https://"):
            raise gl.vm.UserError("Origin is invalid")

        if not normalized.startswith("https://"):
            raise gl.vm.UserError("Origin must use https://")

        return normalized

    def _location_matches_origin(self, location: str, origin: str) -> bool:
        normalized_location = location.strip()

        return (
            normalized_location == origin
            or normalized_location.startswith(origin + "/")
            or normalized_location.startswith(origin + "?")
            or normalized_location.startswith(origin + "#")
        )

    def _require_authority(
        self,
        authority_id: u256,
        revision: u256,
    ) -> AuthorityRevision:
        key = self._authority_key(authority_id, revision)

        if not self.authority_exists.get(key, False):
            raise gl.vm.UserError("Authority revision does not exist")

        return self.authorities[key]

    def _require_policy(
        self,
        policy_id: u256,
        version: u256,
    ) -> PolicyVersion:
        key = self._policy_key(policy_id, version)

        if not self.policy_exists.get(key, False):
            raise gl.vm.UserError("Policy version does not exist")

        return self.policies[key]

    def _require_bundle(self, bundle_id: u256) -> EvidenceBundle:
        key = self._bundle_key(bundle_id)

        if not self.bundle_exists.get(key, False):
            raise gl.vm.UserError("Bundle does not exist")

        return self.bundles[key]

    def _require_challenge(
        self,
        challenge_id: u256,
    ) -> ChallengeRequest:
        key = self._challenge_key(challenge_id)

        if not self.challenge_exists.get(key, False):
            raise gl.vm.UserError("Challenge does not exist")

        return self.challenges[key]

    def _authority_is_currently_revoked(
        self,
        authority_id: u256,
        revision: u256,
    ) -> bool:
        key = self._authority_key(authority_id, revision)
        return self.authority_revoked_at.get(key, u256(0)) != u256(0)

    def _authority_is_currently_valid(
        self,
        authority: AuthorityRevision,
    ) -> bool:
        now = self._now()

        if self._authority_is_currently_revoked(
            authority.authority_id,
            authority.revision,
        ):
            return False

        if authority.valid_until != u256(0) and now > authority.valid_until:
            return False

        return now >= authority.valid_from

    def _policy_authority_key(
        self,
        policy_key: str,
        role: str,
        authority_key: str,
    ) -> str:
        return f"{policy_key}|{role}|{authority_key}"

    def _policy_group_key(
        self,
        policy_key: str,
        independence_group: str,
    ) -> str:
        return f"{policy_key}|{independence_group}"

    def _bundle_authority_key(
        self,
        bundle_key: str,
        authority_key: str,
    ) -> str:
        return f"{bundle_key}|{authority_key}"

    def _create_bundle_internal(
        self,
        policy_id: u256,
        policy_version: u256,
        claim: str,
        supersedes_bundle_id: u256,
    ) -> u256:
        policy = self._require_policy(policy_id, policy_version)
        policy_key = self._policy_key(policy_id, policy_version)

        if not policy.sealed:
            raise gl.vm.UserError("Policy version is not sealed")

        if self.policy_activated_at.get(policy_key, u256(0)) == u256(0):
            raise gl.vm.UserError("Policy version is not active")

        normalized_claim = claim.strip()
        if not normalized_claim:
            raise gl.vm.UserError("Claim is required")

        bundle_id = self.next_bundle_id
        self.next_bundle_id = u256(int(self.next_bundle_id) + 1)

        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            policy_id=policy_id,
            policy_version=policy_version,
            claim=normalized_claim,
            fact_namespace=policy.fact_namespace,
            submitted_by=gl.message.sender_address,
            submitted_at=self._now(),
            supersedes_bundle_id=supersedes_bundle_id,
            primary_record_id=u256(0),
            record_count=u256(0),
            corroborator_count=u256(0),
            frozen=False,
        )

        bundle_key = self._bundle_key(bundle_id)
        self.bundles[bundle_key] = bundle
        self.bundle_exists[bundle_key] = True

        return bundle_id

    # ------------------------------------------------------------------
    # Authority revisions
    # ------------------------------------------------------------------

    @gl.public.write
    def create_authority(
        self,
        name: str,
        independence_group: str,
        valid_until: int,
    ) -> int:
        self._only_owner()

        normalized_name = name.strip()
        normalized_group = independence_group.strip()

        if not normalized_name:
            raise gl.vm.UserError("Authority name is required")

        if not normalized_group:
            raise gl.vm.UserError("Independence group is required")

        now = self._now()

        if valid_until < 0:
            raise gl.vm.UserError("valid_until cannot be negative")

        if valid_until != 0 and valid_until <= int(now):
            raise gl.vm.UserError("valid_until must be in the future")

        authority_id = self.next_authority_id
        self.next_authority_id = u256(int(self.next_authority_id) + 1)

        revision = u256(1)
        key = self._authority_key(authority_id, revision)

        self.authorities[key] = AuthorityRevision(
            authority_id=authority_id,
            revision=revision,
            name=normalized_name,
            independence_group=normalized_group,
            valid_from=now,
            valid_until=u256(valid_until),
            sealed=False,
        )

        self.authority_exists[key] = True
        self.authority_latest_revision[
            self._authority_id_key(authority_id)
        ] = revision

        return int(authority_id)

    @gl.public.write
    def create_authority_revision(
        self,
        authority_id: int,
        name: str,
        independence_group: str,
        valid_until: int,
    ) -> int:
        self._only_owner()

        aid = self._id(authority_id, "authority_id")
        aid_key = self._authority_id_key(aid)

        latest = self.authority_latest_revision.get(aid_key, u256(0))

        if latest == u256(0):
            raise gl.vm.UserError("Authority does not exist")

        previous = self._require_authority(aid, latest)

        if not previous.sealed:
            raise gl.vm.UserError("Previous authority revision must be sealed")

        normalized_name = name.strip()
        normalized_group = independence_group.strip()

        if not normalized_name:
            raise gl.vm.UserError("Authority name is required")

        if not normalized_group:
            raise gl.vm.UserError("Independence group is required")

        now = self._now()

        if valid_until < 0:
            raise gl.vm.UserError("valid_until cannot be negative")

        if valid_until != 0 and valid_until <= int(now):
            raise gl.vm.UserError("valid_until must be in the future")

        revision = u256(int(latest) + 1)
        key = self._authority_key(aid, revision)

        self.authorities[key] = AuthorityRevision(
            authority_id=aid,
            revision=revision,
            name=normalized_name,
            independence_group=normalized_group,
            valid_from=now,
            valid_until=u256(valid_until),
            sealed=False,
        )

        self.authority_exists[key] = True
        self.authority_latest_revision[aid_key] = revision

        return int(revision)

    @gl.public.write
    def add_authority_origin(
        self,
        authority_id: int,
        revision: int,
        origin: str,
    ) -> None:
        self._only_owner()

        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")
        authority = self._require_authority(aid, rev)

        if authority.sealed:
            raise gl.vm.UserError("Authority revision is sealed")

        normalized_origin = self._normalize_origin(origin)
        authority_key = self._authority_key(aid, rev)
        membership_key = f"{authority_key}|{normalized_origin}"

        if self.authority_origin_membership.get(membership_key, False):
            raise gl.vm.UserError("Authority origin already exists")

        count = self.authority_origin_count.get(authority_key, u256(0))
        index = u256(int(count) + 1)

        self.authority_origins[
            f"{authority_key}|{index}"
        ] = normalized_origin

        self.authority_origin_count[authority_key] = index
        self.authority_origin_membership[membership_key] = True

    @gl.public.write
    def seal_authority_revision(
        self,
        authority_id: int,
        revision: int,
    ) -> None:
        self._only_owner()

        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")
        authority = self._require_authority(aid, rev)

        if authority.sealed:
            raise gl.vm.UserError("Authority revision is already sealed")

        authority_key = self._authority_key(aid, rev)

        if self.authority_origin_count.get(
            authority_key,
            u256(0),
        ) == u256(0):
            raise gl.vm.UserError("Authority revision requires an origin")

        authority.sealed = True

    @gl.public.write
    def revoke_authority_revision(
        self,
        authority_id: int,
        revision: int,
    ) -> None:
        self._only_owner()

        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")
        authority = self._require_authority(aid, rev)

        if not authority.sealed:
            raise gl.vm.UserError("Authority revision must be sealed")

        key = self._authority_key(aid, rev)

        if self.authority_revoked_at.get(key, u256(0)) != u256(0):
            raise gl.vm.UserError("Authority revision already revoked")

        # Revocation is lifecycle metadata. The sealed authority
        # definition itself remains unchanged.
        self.authority_revoked_at[key] = self._now()

    # ------------------------------------------------------------------
    # Immutable policy versions
    # ------------------------------------------------------------------

    @gl.public.write
    def create_policy(
        self,
        name: str,
        minimum_independent_corroborators: int,
        maximum_evidence_age: int,
        fact_namespace: str,
    ) -> int:
        self._only_owner()

        normalized_name = name.strip()
        normalized_namespace = fact_namespace.strip()

        if not normalized_name:
            raise gl.vm.UserError("Policy name is required")

        if minimum_independent_corroborators <= 0:
            raise gl.vm.UserError(
                "At least one independent corroborator is required"
            )

        if minimum_independent_corroborators >= MAX_BUNDLE_EVIDENCE_RECORDS:
            raise gl.vm.UserError(
                "minimum_independent_corroborators exceeds bundle limit"
            )

        if maximum_evidence_age <= 0:
            raise gl.vm.UserError("maximum_evidence_age must be positive")

        if not normalized_namespace:
            raise gl.vm.UserError("Fact namespace is required")

        policy_id = self.next_policy_id
        self.next_policy_id = u256(int(self.next_policy_id) + 1)

        version = u256(1)
        key = self._policy_key(policy_id, version)

        self.policies[key] = PolicyVersion(
            policy_id=policy_id,
            version=version,
            name=normalized_name,
            minimum_independent_corroborators=u256(
                minimum_independent_corroborators
            ),
            maximum_evidence_age=u256(maximum_evidence_age),
            fact_namespace=normalized_namespace,
            sealed=False,
        )

        self.policy_exists[key] = True
        self.policy_latest_version[
            self._policy_id_key(policy_id)
        ] = version

        return int(policy_id)

    @gl.public.write
    def create_policy_revision(
        self,
        policy_id: int,
        name: str,
        minimum_independent_corroborators: int,
        maximum_evidence_age: int,
        fact_namespace: str,
    ) -> int:
        self._only_owner()

        pid = self._id(policy_id, "policy_id")
        pid_key = self._policy_id_key(pid)

        latest = self.policy_latest_version.get(pid_key, u256(0))

        if latest == u256(0):
            raise gl.vm.UserError("Policy does not exist")

        previous = self._require_policy(pid, latest)

        if not previous.sealed:
            raise gl.vm.UserError("Previous policy version must be sealed")

        normalized_name = name.strip()
        normalized_namespace = fact_namespace.strip()

        if not normalized_name:
            raise gl.vm.UserError("Policy name is required")

        if minimum_independent_corroborators <= 0:
            raise gl.vm.UserError(
                "At least one independent corroborator is required"
            )

        if minimum_independent_corroborators >= MAX_BUNDLE_EVIDENCE_RECORDS:
            raise gl.vm.UserError(
                "minimum_independent_corroborators exceeds bundle limit"
            )

        if maximum_evidence_age <= 0:
            raise gl.vm.UserError("maximum_evidence_age must be positive")

        if not normalized_namespace:
            raise gl.vm.UserError("Fact namespace is required")

        version = u256(int(latest) + 1)
        key = self._policy_key(pid, version)

        self.policies[key] = PolicyVersion(
            policy_id=pid,
            version=version,
            name=normalized_name,
            minimum_independent_corroborators=u256(
                minimum_independent_corroborators
            ),
            maximum_evidence_age=u256(maximum_evidence_age),
            fact_namespace=normalized_namespace,
            sealed=False,
        )

        self.policy_exists[key] = True
        self.policy_latest_version[pid_key] = version

        return int(version)

    @gl.public.write
    def add_policy_authority(
        self,
        policy_id: int,
        version: int,
        authority_id: int,
        authority_revision: int,
        role: str,
    ) -> None:
        self._only_owner()

        pid = self._id(policy_id, "policy_id")
        ver = self._id(version, "version")
        aid = self._id(authority_id, "authority_id")
        arev = self._id(authority_revision, "authority_revision")

        policy = self._require_policy(pid, ver)

        if policy.sealed:
            raise gl.vm.UserError("Policy version is sealed")

        if role not in (ROLE_PRIMARY, ROLE_CORROBORATOR):
            raise gl.vm.UserError("Invalid authority role")

        authority = self._require_authority(aid, arev)

        if not authority.sealed:
            raise gl.vm.UserError("Authority revision must be sealed")

        if not self._authority_is_currently_valid(authority):
            raise gl.vm.UserError("Authority revision is not currently valid")

        policy_key = self._policy_key(pid, ver)
        authority_key = self._authority_key(aid, arev)

        membership_key = self._policy_authority_key(
            policy_key,
            role,
            authority_key,
        )

        if self.policy_authority_membership.get(membership_key, False):
            raise gl.vm.UserError("Authority already registered in policy")

        # A single organizational independence group cannot occupy
        # multiple policy slots, including primary-vs-corroborator slots.
        group_key = self._policy_group_key(
            policy_key,
            authority.independence_group,
        )

        if self.policy_independence_group_used.get(group_key, False):
            raise gl.vm.UserError(
                "Independence group already used in policy"
            )

        self.policy_authority_membership[membership_key] = True
        self.policy_independence_group_used[group_key] = True

        if role == ROLE_PRIMARY:
            count = self.policy_primary_count.get(policy_key, u256(0))
            self.policy_primary_count[policy_key] = u256(int(count) + 1)
        else:
            count = self.policy_corroborator_count.get(
                policy_key,
                u256(0),
            )
            self.policy_corroborator_count[policy_key] = u256(
                int(count) + 1
            )

    @gl.public.write
    def activate_policy(
        self,
        policy_id: int,
        version: int,
    ) -> None:
        self._only_owner()

        pid = self._id(policy_id, "policy_id")
        ver = self._id(version, "version")
        policy = self._require_policy(pid, ver)
        policy_key = self._policy_key(pid, ver)

        if policy.sealed:
            raise gl.vm.UserError("Policy version is already sealed")

        if self.policy_primary_count.get(
            policy_key,
            u256(0),
        ) == u256(0):
            raise gl.vm.UserError("Policy requires a primary authority")

        corroborator_count = self.policy_corroborator_count.get(
            policy_key,
            u256(0),
        )

        if corroborator_count < policy.minimum_independent_corroborators:
            raise gl.vm.UserError(
                "Policy has insufficient corroborating authorities"
            )

        policy.sealed = True
        self.policy_activated_at[policy_key] = self._now()

    # ------------------------------------------------------------------
    # Evidence bundles
    # ------------------------------------------------------------------

    @gl.public.write
    def create_bundle(
        self,
        policy_id: int,
        policy_version: int,
        claim: str,
    ) -> int:
        pid = self._id(policy_id, "policy_id")
        version = self._id(policy_version, "policy_version")

        bundle_id = self._create_bundle_internal(
            pid,
            version,
            claim,
            u256(0),
        )

        return int(bundle_id)

    @gl.public.write
    def add_evidence_record(
        self,
        bundle_id: int,
        authority_id: int,
        authority_revision: int,
        retrieval_origin: str,
        retrieval_location: str,
        version_reference: str,
        submitted_digest: str,
        claimed_published_at: int,
        is_primary: bool,
    ) -> int:
        bid = self._id(bundle_id, "bundle_id")
        aid = self._id(authority_id, "authority_id")
        arev = self._id(authority_revision, "authority_revision")

        bundle = self._require_bundle(bid)

        if bundle.submitted_by != gl.message.sender_address:
            raise gl.vm.UserError("Only bundle submitter")

        if bundle.frozen:
            raise gl.vm.UserError("Bundle is frozen")

        authority = self._require_authority(aid, arev)

        if not authority.sealed:
            raise gl.vm.UserError("Authority revision must be sealed")

        if not self._authority_is_currently_valid(authority):
            raise gl.vm.UserError("Authority revision is not currently valid")

        policy_key = self._policy_key(
            bundle.policy_id,
            bundle.policy_version,
        )
        authority_key = self._authority_key(aid, arev)

        role = ROLE_PRIMARY if is_primary else ROLE_CORROBORATOR

        membership_key = self._policy_authority_key(
            policy_key,
            role,
            authority_key,
        )

        if not self.policy_authority_membership.get(
            membership_key,
            False,
        ):
            raise gl.vm.UserError(
                "Authority revision is not approved for this policy role"
            )

        normalized_origin = self._normalize_origin(retrieval_origin)

        if not self.authority_origin_membership.get(
            f"{authority_key}|{normalized_origin}",
            False,
        ):
            raise gl.vm.UserError("Evidence origin is not approved")

        normalized_location = retrieval_location.strip()

        if not self._location_matches_origin(
            normalized_location,
            normalized_origin,
        ):
            raise gl.vm.UserError(
                "Evidence location does not match approved origin"
            )

        normalized_version = version_reference.strip()
        normalized_digest = submitted_digest.strip()

        if not normalized_version:
            raise gl.vm.UserError("Version reference is required")

        if not normalized_digest:
            raise gl.vm.UserError("Submitted digest is required")

        now = self._now()

        if claimed_published_at <= 0:
            raise gl.vm.UserError("claimed_published_at must be positive")

        if claimed_published_at > int(now):
            raise gl.vm.UserError(
                "claimed_published_at cannot be in the future"
            )

        bundle_key = self._bundle_key(bid)
        bundle_authority_key = self._bundle_authority_key(
            bundle_key,
            authority_key,
        )

        if self.bundle_authority_used.get(
            bundle_authority_key,
            False,
        ):
            raise gl.vm.UserError(
                "Authority revision already used in bundle"
            )

        if is_primary and bundle.primary_record_id != u256(0):
            raise gl.vm.UserError("Bundle already has a primary record")

        if int(bundle.record_count) >= MAX_BUNDLE_EVIDENCE_RECORDS:
            raise gl.vm.UserError(
                "Bundle evidence record limit reached"
            )

        record_id = self.next_record_id
        self.next_record_id = u256(int(self.next_record_id) + 1)

        record = EvidenceRecord(
            record_id=record_id,
            bundle_id=bid,
            authority_id=aid,
            authority_revision=arev,
            retrieval_origin=normalized_origin,
            retrieval_location=normalized_location,
            version_reference=normalized_version,
            submitted_digest=normalized_digest,
            # This field remains a claimant assertion.
            # It will NOT be used as trusted freshness evidence.
            claimed_published_at=u256(claimed_published_at),
            submitted_at=now,
            is_primary=is_primary,
        )

        record_key = self._record_key(record_id)
        self.records[record_key] = record
        self.record_exists[record_key] = True

        self.bundle_authority_used[bundle_authority_key] = True

        record_index = u256(int(bundle.record_count) + 1)

        self.bundle_record_ids[
            f"{bundle_key}|{record_index}"
        ] = record_id

        bundle.record_count = record_index

        if is_primary:
            bundle.primary_record_id = record_id
        else:
            bundle.corroborator_count = u256(
                int(bundle.corroborator_count) + 1
            )

        return int(record_id)

    @gl.public.write
    def freeze_bundle(self, bundle_id: int) -> None:
        bid = self._id(bundle_id, "bundle_id")
        bundle = self._require_bundle(bid)

        if bundle.submitted_by != gl.message.sender_address:
            raise gl.vm.UserError("Only bundle submitter")

        if bundle.frozen:
            raise gl.vm.UserError("Bundle is already frozen")

        if bundle.primary_record_id == u256(0):
            raise gl.vm.UserError("Bundle requires a primary record")

        policy = self._require_policy(
            bundle.policy_id,
            bundle.policy_version,
        )

        if (
            bundle.corroborator_count
            < policy.minimum_independent_corroborators
        ):
            raise gl.vm.UserError(
                "Bundle has insufficient corroborating records"
            )

        bundle.frozen = True

    @gl.public.write
    def create_superseding_bundle(
        self,
        bundle_id: int,
    ) -> int:
        old_id = self._id(bundle_id, "bundle_id")
        old_bundle = self._require_bundle(old_id)

        if old_bundle.submitted_by != gl.message.sender_address:
            raise gl.vm.UserError("Only bundle submitter")

        if not old_bundle.frozen:
            raise gl.vm.UserError(
                "Only a frozen bundle can be superseded"
            )

        old_key = self._bundle_key(old_id)

        if self.bundle_superseded_by.get(
            old_key,
            u256(0),
        ) != u256(0):
            raise gl.vm.UserError("Bundle already has a superseding bundle")

        new_id = self._create_bundle_internal(
            old_bundle.policy_id,
            old_bundle.policy_version,
            old_bundle.claim,
            old_id,
        )

        self.bundle_superseded_by[old_key] = new_id

        return int(new_id)

    # ------------------------------------------------------------------
    # Challenge-request lifecycle
    # ------------------------------------------------------------------
    #
    # SECURITY INVARIANT:
    #
    # A challenge request is only a request for fresh evidence review.
    # Submission alone MUST NOT change bundle admissibility, permit
    # validity, authorization, or any other consequential state.
    #
    # A future validator-backed materiality review is the ONLY path
    # allowed to populate bundle_open_challenge_id.
    #
    # This prevents an attacker from blocking a valid bundle merely by
    # submitting an arbitrary URL or unsupported allegation.
    # ------------------------------------------------------------------

    @gl.public.write
    def submit_challenge_request(
        self,
        bundle_id: int,
        evidence_reference: str,
        evidence_digest: str,
        reason: str,
    ) -> int:
        bid = self._id(bundle_id, "bundle_id")
        bundle = self._require_bundle(bid)

        if not bundle.frozen:
            raise gl.vm.UserError(
                "Only frozen bundles can receive challenge requests"
            )

        bundle_key = self._bundle_key(bid)

        if self.bundle_superseded_by.get(
            bundle_key,
            u256(0),
        ) != u256(0):
            raise gl.vm.UserError(
                "Superseded bundle cannot receive challenge request"
            )

        normalized_reference = evidence_reference.strip()
        normalized_digest = evidence_digest.strip()
        normalized_reason = reason.strip()

        if not normalized_reference:
            raise gl.vm.UserError(
                "Challenge request requires evidence reference"
            )

        if not normalized_reference.startswith("https://"):
            raise gl.vm.UserError(
                "Challenge evidence reference must use https://"
            )

        if not normalized_digest:
            raise gl.vm.UserError(
                "Challenge request requires evidence digest"
            )

        if not normalized_reason:
            raise gl.vm.UserError(
                "Challenge reason is required"
            )

        if self.bundle_pending_challenge_id.get(
            bundle_key,
            u256(0),
        ) != u256(0):
            raise gl.vm.UserError(
                "Bundle already has a pending challenge request"
            )

        # A confirmed open challenge, once the validator-backed review
        # layer exists, also prevents a second pending request.
        if self.bundle_open_challenge_id.get(
            bundle_key,
            u256(0),
        ) != u256(0):
            raise gl.vm.UserError(
                "Bundle already has an open challenge"
            )

        now = self._now()

        challenge_id = self.next_challenge_id
        self.next_challenge_id = u256(
            int(self.next_challenge_id) + 1
        )

        challenge = ChallengeRequest(
            challenge_id=challenge_id,
            bundle_id=bid,
            submitted_by=gl.message.sender_address,
            evidence_reference=normalized_reference,
            evidence_digest=normalized_digest,
            reason=normalized_reason,
            submitted_at=now,
            deadline=u256(
                int(now) + int(self.challenge_window_seconds)
            ),
            expired=False,
        )

        challenge_key = self._challenge_key(challenge_id)

        self.challenges[challenge_key] = challenge
        self.challenge_exists[challenge_key] = True

        # Deliberately pending only.
        #
        # DO NOT set bundle_open_challenge_id here.
        self.bundle_pending_challenge_id[
            bundle_key
        ] = challenge_id

        return int(challenge_id)

    @gl.public.write
    def expire_challenge_request(
        self,
        challenge_id: int,
    ) -> None:
        cid = self._id(challenge_id, "challenge_id")
        challenge = self._require_challenge(cid)

        if challenge.expired:
            raise gl.vm.UserError(
                "Challenge request is already expired"
            )

        now = self._now()

        if now <= challenge.deadline:
            raise gl.vm.UserError(
                "Challenge request deadline not reached"
            )

        challenge.expired = True

        bundle_key = self._bundle_key(
            challenge.bundle_id
        )

        # Expiring an unreviewed request only removes the pending
        # request. It does NOT modify consequential challenge state.
        if self.bundle_pending_challenge_id.get(
            bundle_key,
            u256(0),
        ) == cid:
            self.bundle_pending_challenge_id[
                bundle_key
            ] = u256(0)

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    @gl.public.view
    def get_owner(self) -> str:
        return str(self.owner)

    @gl.public.view
    def get_challenge_window_seconds(self) -> int:
        return int(self.challenge_window_seconds)

    @gl.public.view
    def get_latest_authority_revision(
        self,
        authority_id: int,
    ) -> int:
        aid = self._id(authority_id, "authority_id")
        return int(
            self.authority_latest_revision.get(
                self._authority_id_key(aid),
                u256(0),
            )
        )

    @gl.public.view
    def is_authority_sealed(
        self,
        authority_id: int,
        revision: int,
    ) -> bool:
        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")
        return self._require_authority(aid, rev).sealed

    @gl.public.view
    def get_authority_origin_count(
        self,
        authority_id: int,
        revision: int,
    ) -> int:
        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")

        self._require_authority(aid, rev)

        return int(
            self.authority_origin_count.get(
                self._authority_key(aid, rev),
                u256(0),
            )
        )

    @gl.public.view
    def get_authority_origin(
        self,
        authority_id: int,
        revision: int,
        index: int,
    ) -> str:
        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")

        if index <= 0:
            raise gl.vm.UserError("index must be positive")

        self._require_authority(aid, rev)

        return self.authority_origins.get(
            f"{self._authority_key(aid, rev)}|{u256(index)}",
            "",
        )

    @gl.public.view
    def get_authority_revoked_at(
        self,
        authority_id: int,
        revision: int,
    ) -> int:
        aid = self._id(authority_id, "authority_id")
        rev = self._id(revision, "revision")

        self._require_authority(aid, rev)

        return int(
            self.authority_revoked_at.get(
                self._authority_key(aid, rev),
                u256(0),
            )
        )

    @gl.public.view
    def get_latest_policy_version(self, policy_id: int) -> int:
        pid = self._id(policy_id, "policy_id")

        return int(
            self.policy_latest_version.get(
                self._policy_id_key(pid),
                u256(0),
            )
        )

    @gl.public.view
    def is_policy_sealed(
        self,
        policy_id: int,
        version: int,
    ) -> bool:
        pid = self._id(policy_id, "policy_id")
        ver = self._id(version, "version")

        return self._require_policy(pid, ver).sealed

    @gl.public.view
    def get_policy_authority_count(
        self,
        policy_id: int,
        version: int,
        role: str,
    ) -> int:
        pid = self._id(policy_id, "policy_id")
        ver = self._id(version, "version")
        policy_key = self._policy_key(pid, ver)

        self._require_policy(pid, ver)

        if role == ROLE_PRIMARY:
            return int(
                self.policy_primary_count.get(
                    policy_key,
                    u256(0),
                )
            )

        if role == ROLE_CORROBORATOR:
            return int(
                self.policy_corroborator_count.get(
                    policy_key,
                    u256(0),
                )
            )

        raise gl.vm.UserError("Invalid authority role")

    @gl.public.view
    def is_policy_active(
        self,
        policy_id: int,
        version: int,
    ) -> bool:
        pid = self._id(policy_id, "policy_id")
        ver = self._id(version, "version")

        self._require_policy(pid, ver)

        return (
            self.policy_activated_at.get(
                self._policy_key(pid, ver),
                u256(0),
            )
            != u256(0)
        )

    @gl.public.view
    def is_bundle_frozen(self, bundle_id: int) -> bool:
        bid = self._id(bundle_id, "bundle_id")
        return self._require_bundle(bid).frozen

    @gl.public.view
    def get_bundle_policy_id(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).policy_id)

    @gl.public.view
    def get_bundle_policy_version(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).policy_version)

    @gl.public.view
    def get_bundle_primary_record_id(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).primary_record_id)

    @gl.public.view
    def get_bundle_record_count(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).record_count)

    @gl.public.view
    def get_bundle_corroborator_count(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).corroborator_count)

    @gl.public.view
    def get_bundle_supersedes(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        return int(self._require_bundle(bid).supersedes_bundle_id)

    @gl.public.view
    def get_bundle_superseded_by(self, bundle_id: int) -> int:
        bid = self._id(bundle_id, "bundle_id")
        self._require_bundle(bid)

        return int(
            self.bundle_superseded_by.get(
                self._bundle_key(bid),
                u256(0),
            )
        )

    @gl.public.view
    def bundle_has_pending_challenge_request(
        self,
        bundle_id: int,
    ) -> bool:
        bid = self._id(bundle_id, "bundle_id")
        self._require_bundle(bid)

        return (
            self.bundle_pending_challenge_id.get(
                self._bundle_key(bid),
                u256(0),
            )
            != u256(0)
        )

    @gl.public.view
    def get_pending_challenge_id(
        self,
        bundle_id: int,
    ) -> int:
        bid = self._id(bundle_id, "bundle_id")
        self._require_bundle(bid)

        return int(
            self.bundle_pending_challenge_id.get(
                self._bundle_key(bid),
                u256(0),
            )
        )

    @gl.public.view
    def bundle_has_open_challenge(
        self,
        bundle_id: int,
    ) -> bool:
        bid = self._id(bundle_id, "bundle_id")
        self._require_bundle(bid)

        # This map is intentionally never populated by mere request
        # submission. Future validator-backed materiality review will
        # be the only writer.
        return (
            self.bundle_open_challenge_id.get(
                self._bundle_key(bid),
                u256(0),
            )
            != u256(0)
        )

    @gl.public.view
    def get_open_challenge_id(
        self,
        bundle_id: int,
    ) -> int:
        bid = self._id(bundle_id, "bundle_id")
        self._require_bundle(bid)

        return int(
            self.bundle_open_challenge_id.get(
                self._bundle_key(bid),
                u256(0),
            )
        )

    @gl.public.view
    def get_challenge_deadline(
        self,
        challenge_id: int,
    ) -> int:
        cid = self._id(challenge_id, "challenge_id")
        return int(
            self._require_challenge(cid).deadline
        )

    @gl.public.view
    def is_challenge_request_expired(
        self,
        challenge_id: int,
    ) -> bool:
        cid = self._id(challenge_id, "challenge_id")
        return self._require_challenge(cid).expired


    # ------------------------------------------------------------------
    # Append-only review ledger
    # ------------------------------------------------------------------
    #
    # No public method creates or modifies ReviewRecord yet.
    #
    # Future validator-backed adjudication is the only intended writer.
    # ------------------------------------------------------------------

    def _review_key(
        self,
        review_id: u256,
    ) -> str:
        return str(int(review_id))

    def _require_review(
        self,
        review_id: u256,
    ) -> ReviewRecord:
        key = self._review_key(review_id)

        if not self.review_exists.get(
            key,
            False,
        ):
            raise gl.vm.UserError(
                "Review does not exist"
            )

        return self.reviews[key]

    @gl.public.view
    def get_bundle_review_count(
        self,
        bundle_id: int,
    ) -> int:
        bid = self._id(
            bundle_id,
            "bundle_id",
        )

        self._require_bundle(bid)

        return int(
            self.bundle_review_count.get(
                self._bundle_key(bid),
                u256(0),
            )
        )

    @gl.public.view
    def get_latest_review_id(
        self,
        bundle_id: int,
    ) -> int:
        bid = self._id(
            bundle_id,
            "bundle_id",
        )

        self._require_bundle(bid)

        return int(
            self.bundle_latest_review_id.get(
                self._bundle_key(bid),
                u256(0),
            )
        )

    @gl.public.view
    def get_review_bundle_id(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).bundle_id
        )

    @gl.public.view
    def get_review_attempt_number(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).attempt_number
        )

    @gl.public.view
    def get_review_previous_id(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).previous_review_id
        )

    @gl.public.view
    def get_review_kind(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).review_kind

    @gl.public.view
    def get_review_challenge_request_id(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).challenge_request_id
        )

    @gl.public.view
    def get_review_policy_id(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).policy_id
        )

    @gl.public.view
    def get_review_policy_version(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).policy_version
        )

    @gl.public.view
    def get_review_status(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).status

    @gl.public.view
    def get_review_fact_code(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).fact_code

    @gl.public.view
    def get_review_verified_primary_version(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).verified_primary_version

    @gl.public.view
    def get_review_verified_primary_published_at(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).verified_primary_published_at
        )

    @gl.public.view
    def get_review_qualifying_authority_set(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).qualifying_authority_set

    @gl.public.view
    def get_review_excluded_authority_set(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).excluded_authority_set

    @gl.public.view
    def get_review_evidence_facts_canonical(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).evidence_facts_canonical

    @gl.public.view
    def get_review_independent_corroborator_count(
        self,
        review_id: int,
    ) -> int:
        rid = self._id(
            review_id,
            "review_id",
        )

        return int(
            self._require_review(
                rid
            ).independent_corroborator_count
        )

    @gl.public.view
    def get_review_conflict_detected(
        self,
        review_id: int,
    ) -> bool:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).conflict_detected

    @gl.public.view
    def get_review_reason_code(
        self,
        review_id: int,
    ) -> str:
        rid = self._id(
            review_id,
            "review_id",
        )

        return self._require_review(
            rid
        ).reason_code


    @gl.public.view
    def get_bundle_record_id(
        self,
        bundle_id: int,
        record_index: int,
    ) -> int:
        bid = self._id(
            bundle_id,
            "bundle_id",
        )

        bundle = self._require_bundle(bid)

        if record_index <= 0:
            raise gl.vm.UserError(
                "record_index must be positive"
            )

        if record_index > int(bundle.record_count):
            raise gl.vm.UserError(
                "record_index exceeds bundle record count"
            )

        record_id = self.bundle_record_ids.get(
            f"{self._bundle_key(bid)}|{record_index}",
            u256(0),
        )

        if record_id == u256(0):
            raise gl.vm.UserError(
                "Bundle record index is inconsistent"
            )

        return int(record_id)

    @gl.public.view
    def get_max_bundle_evidence_records(
        self,
    ) -> int:
        return MAX_BUNDLE_EVIDENCE_RECORDS
