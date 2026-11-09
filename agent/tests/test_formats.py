import pytest

from firewall_agent.formats import (
    ContextItem,
    PaymentRequest,
    amount_to_units,
    compact_json,
    units_to_display,
)


@pytest.mark.parametrize(
    "text,units",
    [("18", 18_000_000), ("18.5", 18_500_000), ("0.000001", 1), ("180", 180_000_000)],
)
def test_amount_ok(text, units):
    assert amount_to_units(text, 6) == units


@pytest.mark.parametrize("text", ["0.0000001", "0", "-1", "abc", "", "1e3", "0.0"])
def test_amount_rejected(text):
    with pytest.raises(ValueError):
        amount_to_units(text, 6)


def test_units_to_display():
    assert units_to_display(18_000_000, 6) == "18"
    assert units_to_display(18_500_000, 6) == "18.5"
    assert units_to_display(1, 6) == "0.000001"


def _req(context):
    return PaymentRequest("ref-1", "hostco.demo.testnet", 1, "m", "pay it", context)


def _item_with_total(total_bytes: int) -> list[ContextItem]:
    item = ContextItem("email", "e", "untrusted", "")
    overhead = len(compact_json([item.to_dict()]))
    item.text = "x" * (total_bytes - overhead)
    ctx = [item]
    assert len(compact_json([c.to_dict() for c in ctx])) == total_bytes
    return ctx


def test_context_limit_boundary():
    _req(_item_with_total(8192)).validate()
    with pytest.raises(ValueError, match="Context too large"):
        _req(_item_with_total(8193)).validate()


def test_too_many_items():
    ctx = [ContextItem("email", f"e{i}", "untrusted", "t") for i in range(9)]
    with pytest.raises(ValueError, match="Too many items"):
        _req(ctx).validate()
    _req(ctx[:8]).validate()
