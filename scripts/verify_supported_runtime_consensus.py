from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from genlayer_py.consensus.consensus_main import encode_tx_data_deploy

ZERO = "0x0000000000000000000000000000000000000000"
SENDER = "0x1111111111111111111111111111111111111111"

HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }\n'

AGREE_SOURCE = HEADER + r'''
from genlayer import *

class RuntimeConsensusProbe(gl.Contract):
    result: str

    def __init__(self):
        def leader_fn():
            return "SOURCEQUORUM_RUNTIME_PROBE_V1"

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            return leader_fn() == leaders_res.calldata

        self.result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
'''

REJECT_SOURCE = HEADER + r'''
from genlayer import *

class RuntimeConsensusProbe(gl.Contract):
    result: str

    def __init__(self):
        def leader_fn():
            return "SOURCEQUORUM_RUNTIME_PROBE_V1"

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            return False

        self.result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
'''


def make_request(source: str, request_id: int, leader_results=None):
    call = {
        "type": "deploy",
        "from": SENDER,
        "to": ZERO,
        "data": encode_tx_data_deploy(source, False, []),
        "value": "0x0",
    }
    if leader_results is not None:
        call["leader_results"] = leader_results
    return {"jsonrpc": "2.0", "method": "gen_call", "params": [call], "id": request_id}


def rpc(rpc_url: str, request: dict, stem: Path) -> dict:
    request_bytes = json.dumps(request, separators=(",", ":")).encode()
    stem.with_suffix(".request.json").write_bytes(request_bytes)

    proc = subprocess.run(
        ["curl", "-fSs", rpc_url, "-H", "content-type: application/json", "--data-binary", "@-"],
        input=request_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    raw = proc.stdout

    raw_path = stem.with_suffix(".raw")
    raw_path.write_bytes(raw)  # persist BEFORE JSON decoding
    return json.loads(raw)


def result_ok(response: dict) -> dict:
    assert response.get("error") is None, response.get("error")
    result = response["result"]
    assert result["status"]["code"] == 0, result["status"]
    return result


def run_pair(rpc_url: str, out: Path, name: str, source: str, reject: bool):
    leader_response = rpc(rpc_url, make_request(source, 1), out / f"{name}-leader")
    leader = result_ok(leader_response)

    assert len(leader["eqOutputs"]) == 1
    assert leader["nondetDisagreementCallNo"] is None

    validator_request = make_request(source, 2, leader["eqOutputs"])
    validator_response = rpc(rpc_url, validator_request, out / f"{name}-validator")
    validator = result_ok(validator_response)

    assert validator["eqOutputs"] == []

    if reject:
        assert validator["nondetDisagreementCallNo"] == 0
    else:
        assert validator["nondetDisagreementCallNo"] is None

    return {
        "leader_eq_outputs": leader["eqOutputs"],
        "validator_eq_outputs": validator["eqOutputs"],
        "nondet_disagreement_call_no": validator["nondetDisagreementCallNo"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc-url", default="https://rpc-bradbury.genlayer.com")
    parser.add_argument("--output-dir", default="artifacts/supported-runtime")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary = {
        "agreement": run_pair(args.rpc_url, out, "agreement", AGREE_SOURCE, False),
        "rejection": run_pair(args.rpc_url, out, "rejection", REJECT_SOURCE, True),
    }

    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("SUPPORTED-RUNTIME CONSENSUS: PASS")


if __name__ == "__main__":
    main()
