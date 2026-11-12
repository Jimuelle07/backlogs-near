import importlib.util

from firewall_agent.config import AGENT_DIR

_spec = importlib.util.spec_from_file_location(
    "bench_lookalike", AGENT_DIR / "tools" / "bench_lookalike.py"
)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)


def test_python_port_matches_rust_cases():
    d = bench.payee_distance
    assert d("cl0udc0x.demo.testnet", "cloudco.demo.testnet") == 1
    assert d("d0m4inr3g.demo.testnet", "domainreg.demo.testnet") == 1
    assert d("supplier-acrne.demo.testnet", "supplier-acme.demo.testnet") == 1
    assert d("hostco.demo.testnet", "hostco.demo.testnet") == 0
    assert bench.ascii_skeleton("Rn_0") == "m-o"
