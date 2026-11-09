"""firewall-setup-testnet: create, deploy and fund the demo accounts on NEAR testnet.

HUMAN-GATED: this signs testnet transactions (account creation, deploy, transfers).
Never run it from an agent session without the human's explicit yes.
Requires: uv sync --extra testnet, and `cargo near build` outputs for contract/token and contract/guardian.
Writes .env.testnet (including GUARDIAN_PRIVATE_KEY), backing up any existing one. Each created account's secret
key goes to .env.testnet.pending right before the account is created (so a lost response cannot strand it), plus the
agent's function-call key before it is added; the file is removed on success and a leftover one stops the next run.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import DEFAULT_TESTNET_RPC, REPO_ROOT, TOKEN_DECIMALS, Settings

TGAS = 10**12
NEAR = 10**24
STORAGE_DEPOSIT = NEAR * 125 // 100_000  # 0.00125 NEAR
USDC = 10**TOKEN_DECIMALS

# name -> initial balance in yoctoNEAR. tusdc gets more than 0.5 NEAR because its wasm
# storage alone is ~2 NEAR (1 NEAR per 100 KB).
ACCOUNTS = {
    "tusdc": 3 * NEAR,
    "guardian": 5 * NEAR,
    "agent": 2 * NEAR,
    "checker": 2 * NEAR,
    "hostco": NEAR // 2,
    "hostc0": NEAR // 2,
}

ENV_TESTNET = REPO_ROOT / ".env.testnet"
ENV_TESTNET_PENDING = REPO_ROOT / ".env.testnet.pending"  # matches the .env.* gitignore rule


def find_wasm(crate: str):
    """cargo-near 0.21.1 writes target/near/<crate>/<crate>.wasm."""
    path = REPO_ROOT / "target" / "near" / crate / f"{crate}.wasm"
    if not path.is_file():
        raise SystemExit(
            f"{path} not found; run in contract/{'token' if crate == 'tusdc' else 'guardian'}: "
            "cargo near build non-reproducible-wasm --no-abi"
        )
    return path


def new_keypair() -> tuple[str, str]:
    """Fresh ed25519 keypair as NEAR strings: (secret 'ed25519:<b58 seed+pub>', public 'ed25519:<b58 pub>')."""
    import base58
    from nacl.signing import SigningKey

    sk = SigningKey.generate()
    pub = bytes(sk.verify_key)
    secret = "ed25519:" + base58.b58encode(bytes(sk) + pub).decode()
    public = "ed25519:" + base58.b58encode(pub).decode()
    return secret, public


def _refuse_if_pending() -> None:
    """A leftover recovery file holds keys of accounts a previous run may have created; never overwrite it."""
    if ENV_TESTNET_PENDING.exists():
        raise SystemExit(
            f"{ENV_TESTNET_PENDING.name} exists: a previous run stopped and may have created accounts. "
            "Inspect it (it holds their secret keys), move it away, then rerun."
        )


def _record_key(account_id: str, secret: str) -> None:
    """Persist an account's secret key before it is created, so a later failure cannot strand its NEAR."""
    new = not ENV_TESTNET_PENDING.exists()
    with ENV_TESTNET_PENDING.open("a", encoding="utf-8") as f:
        if new:
            f.write("# Keys of accounts created by an unfinished firewall-setup-testnet run. Never commit.\n")
        f.write(f"{account_id}={secret}\n")
    print(f"recorded key for {account_id} in {ENV_TESTNET_PENDING.name}")


def _write_env_testnet(lines: list[str], label: str) -> None:
    """Back up any existing .env.testnet, write the new one, then drop the recovery file."""
    if ENV_TESTNET.is_file():
        backup = ENV_TESTNET.with_name(ENV_TESTNET.name + ".v1.bak")
        if backup.exists():
            backup = ENV_TESTNET.with_name(f"{ENV_TESTNET.name}.before-{label}.bak")
        backup.write_bytes(ENV_TESTNET.read_bytes())
        print(f"backed up {ENV_TESTNET.name} to {backup.name}")
    ENV_TESTNET.write_text("\n".join([*lines, ""]), encoding="utf-8")
    ENV_TESTNET_PENDING.unlink(missing_ok=True)
    print(f"done; wrote {ENV_TESTNET.name} (keys not printed)")


async def _run(s: Settings) -> None:
    try:
        from py_near.account import Account
    except ImportError:
        raise SystemExit("py-near not installed; run: uv sync --extra testnet")

    if not (s.owner_account_id and s.owner_private_key):
        raise SystemExit("OWNER_ACCOUNT_ID and OWNER_PRIVATE_KEY must be set in .env")
    owner_id = s.owner_account_id
    rpc = s.near_rpc_url or DEFAULT_TESTNET_RPC
    ids = {name: f"{name}.{owner_id}" for name in ACCOUNTS}
    token_wasm = find_wasm("tusdc").read_bytes()
    guardian_wasm = find_wasm("guardian").read_bytes()
    _refuse_if_pending()

    opened = []
    try:
        owner = Account(owner_id, s.owner_private_key, rpc_addr=rpc)
        opened.append(owner)
        await owner.startup()

        keys: dict[str, tuple[str, str]] = {}
        for name, balance in ACCOUNTS.items():
            keys[name] = new_keypair()
            _record_key(ids[name], keys[name][0])
            print(f"creating {ids[name]}")
            await owner.create_account(ids[name], keys[name][1], balance)

        accts = {}
        for name in ACCOUNTS:
            accts[name] = Account(ids[name], keys[name][0], rpc_addr=rpc)
            opened.append(accts[name])
            await accts[name].startup()

        print("deploying token and guardian")
        await accts["tusdc"].deploy_contract(token_wasm)
        await accts["tusdc"].function_call(ids["tusdc"], "new", {"owner_id": owner_id}, gas=30 * TGAS)
        await accts["guardian"].deploy_contract(guardian_wasm)
        await accts["guardian"].function_call(
            ids["guardian"],
            "new",
            {
                "owner_id": owner_id,
                "agent_id": ids["agent"],
                "token_id": ids["tusdc"],
                "token_decimals": TOKEN_DECIMALS,
                "checker_id": ids["checker"],
            },
            gas=30 * TGAS,
        )

        print("minting 1000 tUSDC to owner")
        await owner.function_call(
            ids["tusdc"], "mint", {"account_id": owner_id, "amount": str(1000 * USDC)}, gas=30 * TGAS
        )
        for name in ("guardian", "hostco", "hostc0"):
            print(f"storage_deposit for {ids[name]}")
            await owner.function_call(
                ids["tusdc"],
                "storage_deposit",
                {"account_id": ids[name], "registration_only": True},
                gas=30 * TGAS,
                amount=STORAGE_DEPOSIT,
            )

        print("funding guardian with 500 tUSDC")
        await owner.function_call(
            ids["tusdc"],
            "ft_transfer_call",
            {"receiver_id": ids["guardian"], "amount": str(500 * USDC), "msg": ""},
            gas=100 * TGAS,
            amount=1,
        )

        print("restricting agent key to a function-call key")
        fc_secret, fc_public = new_keypair()
        _record_key(f"{ids['agent']}#function_call", fc_secret)
        agent = accts["agent"]
        await agent.add_public_key(fc_public, ids["guardian"], ["request_payment"], NEAR)
        await agent.delete_public_key(keys["agent"][1])

        _write_env_testnet(
            [
                "# Written by firewall-setup-testnet. Never commit.",
                f"GUARDIAN_ID={ids['guardian']}",
                f"GUARDIAN_PRIVATE_KEY={keys['guardian'][0]}",
                f"TOKEN_ID={ids['tusdc']}",
                f"AGENT_ACCOUNT_ID={ids['agent']}",
                f"AGENT_PRIVATE_KEY={fc_secret}",
                f"CHECKER_ACCOUNT_ID={ids['checker']}",
                f"CHECKER_PRIVATE_KEY={keys['checker'][0]}",
            ],
            "full",
        )
    finally:
        for acc in opened:
            try:
                await acc.shutdown()
            except Exception as e:
                print(f"shutdown failed: {e}", file=sys.stderr)


async def _redeploy(s: Settings, suffix: str) -> None:
    """Deploy a fresh guardian-{suffix} and agent-{suffix}, reusing the existing tusdc, checker and host accounts."""
    try:
        from py_near.account import Account
    except ImportError:
        raise SystemExit("py-near not installed; run: uv sync --extra testnet")

    if not (s.owner_account_id and s.owner_private_key):
        raise SystemExit("OWNER_ACCOUNT_ID and OWNER_PRIVATE_KEY must be set in .env")
    if not (s.checker_account_id and s.checker_private_key):
        raise SystemExit("CHECKER_ACCOUNT_ID and CHECKER_PRIVATE_KEY must be set in .env.testnet")
    owner_id = s.owner_account_id
    rpc = s.near_rpc_url or DEFAULT_TESTNET_RPC
    guardian_id = f"guardian-{suffix}.{owner_id}"
    agent_id = f"agent-{suffix}.{owner_id}"
    token_id = f"tusdc.{owner_id}"
    guardian_wasm = find_wasm("guardian").read_bytes()
    _refuse_if_pending()

    opened = []
    try:
        owner = Account(owner_id, s.owner_private_key, rpc_addr=rpc)
        opened.append(owner)
        await owner.startup()

        guardian_keys = new_keypair()
        agent_keys = new_keypair()
        _record_key(guardian_id, guardian_keys[0])
        _record_key(agent_id, agent_keys[0])
        print(f"creating {guardian_id}")
        await owner.create_account(guardian_id, guardian_keys[1], 3 * NEAR // 2 + 2 * NEAR)
        print(f"creating {agent_id}")
        await owner.create_account(agent_id, agent_keys[1], NEAR // 2)

        guardian = Account(guardian_id, guardian_keys[0], rpc_addr=rpc)
        opened.append(guardian)
        await guardian.startup()
        agent = Account(agent_id, agent_keys[0], rpc_addr=rpc)
        opened.append(agent)
        await agent.startup()

        print("deploying guardian")
        await guardian.deploy_contract(guardian_wasm)
        await guardian.function_call(
            guardian_id,
            "new",
            {
                "owner_id": owner_id,
                "agent_id": agent_id,
                "token_id": token_id,
                "token_decimals": TOKEN_DECIMALS,
                "checker_id": s.checker_account_id,
            },
            gas=30 * TGAS,
        )

        print(f"storage_deposit for {guardian_id}")
        await owner.function_call(
            token_id,
            "storage_deposit",
            {"account_id": guardian_id, "registration_only": True},
            gas=30 * TGAS,
            amount=STORAGE_DEPOSIT,
        )

        balance = int((await owner.view_function(token_id, "ft_balance_of", {"account_id": owner_id})).result)
        if balance < 200 * USDC:
            print("minting 1000 tUSDC to owner")
            await owner.function_call(
                token_id, "mint", {"account_id": owner_id, "amount": str(1000 * USDC)}, gas=30 * TGAS
            )

        print("funding guardian with 200 tUSDC")
        await owner.function_call(
            token_id,
            "ft_transfer_call",
            {"receiver_id": guardian_id, "amount": str(200 * USDC), "msg": ""},
            gas=100 * TGAS,
            amount=1,
        )

        print("restricting agent key to a function-call key")
        fc_secret, fc_public = new_keypair()
        _record_key(f"{agent_id}#function_call", fc_secret)
        await agent.add_public_key(fc_public, guardian_id, ["request_payment"], NEAR)
        await agent.delete_public_key(agent_keys[1])

        _write_env_testnet(
            [
                "# Written by firewall-setup-testnet --redeploy. Never commit.",
                f"GUARDIAN_ID={guardian_id}",
                f"GUARDIAN_PRIVATE_KEY={guardian_keys[0]}",
                f"TOKEN_ID={token_id}",
                f"AGENT_ACCOUNT_ID={agent_id}",
                f"AGENT_PRIVATE_KEY={fc_secret}",
                f"CHECKER_ACCOUNT_ID={s.checker_account_id}",
                f"CHECKER_PRIVATE_KEY={s.checker_private_key}",
            ],
            suffix,
        )
    finally:
        for acc in opened:
            try:
                await acc.shutdown()
            except Exception as e:
                print(f"shutdown failed: {e}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(prog="firewall-setup-testnet", description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument(
        "--redeploy",
        metavar="SUFFIX",
        help="deploy only guardian-SUFFIX and agent-SUFFIX, reusing tusdc, checker and the host accounts",
    )
    args = ap.parse_args()
    s = Settings.load()
    if s.near_network != "testnet":
        raise SystemExit("NEAR_NETWORK must be testnet")
    if not args.yes:
        ans = input(
            f"This signs testnet transactions as {s.owner_account_id or '<OWNER_ACCOUNT_ID>'}. Type 'yes' to continue: "
        )
        if ans.strip() != "yes":
            raise SystemExit("aborted")
    asyncio.run(_redeploy(s, args.redeploy) if args.redeploy else _run(s))


if __name__ == "__main__":
    main()
