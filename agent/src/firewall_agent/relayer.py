"""firewall-relayer: runs the native checker for pending requests and submits verdicts.

HUMAN-GATED: signs testnet transactions as CHECKER_ACCOUNT_ID. Not attested (scaffold/fallback mode).
"""

from __future__ import annotations

import asyncio
import json
import sys

from .config import Settings
from .guardian import TGAS, binds, run_checker

POLL_SECONDS = 2


async def _retry_once(label: str, fn):
    for attempt in (1, 2):
        try:
            return await fn()
        except Exception as e:  # RPC errors vary by transport
            if attempt == 2:
                print(f"{label} failed: {e}", file=sys.stderr)
                return None


async def _loop(s: Settings) -> None:
    try:
        from py_near.account import Account
    except ImportError:
        raise SystemExit("py-near not installed; run: uv sync --extra testnet")
    for name in ("guardian_id", "checker_account_id", "checker_private_key"):
        if not getattr(s, name):
            raise SystemExit(f"{name.upper()} not set (run firewall-setup-testnet first)")
    rpc = s.near_rpc_url or "https://rpc.testnet.near.org"
    acc = Account(s.checker_account_id, s.checker_private_key, rpc_addr=rpc)
    await acc.startup()
    submitted: set[str] = set()
    print(f"relayer watching {s.guardian_id} as {s.checker_account_id}")
    while True:
        res = await _retry_once(
            "get_pending",
            lambda: acc.view_function(s.guardian_id, "get_pending", {"from_index": 0, "limit": 16}),
        )
        for item in (res.result if res else []) or []:
            rid = str(item["request_id"])
            if rid in submitted:
                continue
            raw = item["checker_input"].encode("utf-8")

            verdict = run_checker(s.checker_bin, raw, s.checker_record_dir / s.guardian_id)
            bad = binds(json.loads(item["checker_input"]), verdict)
            if bad:
                print(f"request {rid}: checker verdict does not bind ({bad}); skipping", file=sys.stderr)
                continue
            ok = await _retry_once(
                f"submit_verdict {rid}",
                lambda: acc.function_call(
                    s.guardian_id,
                    "submit_verdict",
                    {"request_id": rid, "verdict": verdict},
                    gas=100 * TGAS,
                    included=True,
                ),
            )
            if ok is not None:
                submitted.add(rid)
                print(f"request {rid} -> {verdict['outcome']}")
        await asyncio.sleep(POLL_SECONDS)


def main() -> None:
    try:
        asyncio.run(_loop(Settings.load()))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
