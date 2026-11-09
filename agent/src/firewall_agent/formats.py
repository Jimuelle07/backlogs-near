"""Wire-format helpers mirroring schemas/ (the source of truth)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

MAX_CONTEXT_BYTES = 8192
MAX_CONTEXT_ITEMS = 8
SOURCES = ("email", "x_reply", "web", "memory", "tool")
TRUSTS = ("trusted", "untrusted")

_CLIENT_REF = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_ACCOUNT_ID = re.compile(r"^(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$")


def compact_json(value) -> bytes:
    """Compact UTF-8 JSON, preserving key order."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def amount_to_units(amount: str, decimals: int) -> int:
    """Decimal token amount string -> smallest units. Rejects <=0, junk, excess precision."""
    if not isinstance(amount, str):
        raise ValueError("amount must be a string")
    s = amount.strip()
    if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", s):
        raise ValueError(f"invalid amount: {amount!r}")
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"invalid amount: {amount!r}") from e
    if d <= 0:
        raise ValueError("amount must be positive")
    scaled = d * (Decimal(10) ** decimals)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"amount has more than {decimals} fractional digits")
    return int(scaled)


def units_to_display(units: int, decimals: int) -> str:
    whole, frac = divmod(units, 10**decimals)
    if decimals == 0:
        return str(whole)
    frac_s = str(frac).rjust(decimals, "0").rstrip("0")
    return f"{whole}.{frac_s}" if frac_s else str(whole)


@dataclass
class ContextItem:
    source: str
    ref: str
    trust: str
    text: str

    def to_dict(self) -> dict:
        return {"source": self.source, "ref": self.ref, "trust": self.trust, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "ContextItem":
        return cls(source=d["source"], ref=d["ref"], trust=d["trust"], text=d["text"])


@dataclass
class PaymentRequest:
    client_ref: str
    receiver_id: str
    amount: int  # token smallest units
    memo: str
    user_request: str
    context: list[ContextItem] = field(default_factory=list)

    def context_dicts(self) -> list[dict]:
        return [c.to_dict() for c in self.context]

    def to_args(self) -> dict:
        """request_payment args, in schema order (amount is a decimal string)."""
        return {
            "client_ref": self.client_ref,
            "receiver_id": self.receiver_id,
            "amount": str(self.amount),
            "memo": self.memo,
            "user_request": self.user_request,
            "context": self.context_dicts(),
        }

    def validate(self) -> None:
        if not _CLIENT_REF.fullmatch(self.client_ref):
            raise ValueError("Invalid client_ref")
        if not (2 <= len(self.receiver_id) <= 64) or not _ACCOUNT_ID.fullmatch(self.receiver_id):
            raise ValueError("Invalid receiver_id")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("Amount must be positive")
        if len(str(self.amount)) > 39:
            raise ValueError("Invalid amount")
        if len(self.memo) > 256:
            raise ValueError("Invalid memo")
        if not (1 <= len(self.user_request) <= 1024):
            raise ValueError("Invalid user_request")
        if len(compact_json(self.context_dicts())) > MAX_CONTEXT_BYTES:
            raise ValueError("Context too large")
        if len(self.context) > MAX_CONTEXT_ITEMS:
            raise ValueError("Too many items")
        for c in self.context:
            if c.source not in SOURCES:
                raise ValueError("Invalid context source")
            if c.trust not in TRUSTS:
                raise ValueError("Invalid context trust")
            if not (1 <= len(c.ref) <= 128):
                raise ValueError("Invalid context ref")
