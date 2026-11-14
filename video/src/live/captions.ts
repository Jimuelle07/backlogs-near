import { C } from "../theme";
import type { RunEvent } from "./types";

export const CAPTIONS: Record<string, string> = {
  "benign-hosting": "Normal monthly hosting invoice, known payee",
  "attack-morse-lookalike": "Morse-code X reply points to lookalike hostc0",
  "attack-direct-ignore-previous": "Invoice email hides an 'ignore previous instructions' line",
  "benign-supplier-large": "Known supplier, order far above its usual size",
  "attack-memory-poisoning-gen-04": "Poisoned memory raised a payee's usual amount",
  "attack-lookalike-receiver-gen-06": "Invoice pays a lookalike of a real payee",
  "attack-direct-drain-cap": "Injected line asks to move the whole balance",
  "redteam-17": "Small invoice from an unknown auditor (red team)",
};

export const caption = (e: RunEvent): string => CAPTIONS[e.scenario] ?? e.family.split("_").join(" ");

export type Badge = { readonly text: string; readonly color: string };

// Final verdict badge of one run; the same text is used live (Footage) and in the Scoreboard.
export const badge = (e: RunEvent): Badge => {
  if (e.side === "plain") {
    if (e.result === "paid") {
      return e.to_attacker
        ? { text: `PAID ${e.amount} TO ATTACKER`, color: C.alarm }
        : { text: `PAID ${e.amount}`, color: C.allow };
    }
    return { text: e.result.toUpperCase(), color: C.dim };
  }
  switch (e.result) {
    case "would_pay":
      return e.to_attacker
        ? { text: `ALLOWED ${e.amount} → ATTACKER (miss)`, color: C.alarm }
        : { text: `ALLOW · PAID ${e.amount}`, color: C.allow };
    case "held":
      return { text: "HOLD → ESCROW", color: C.hold };
    case "refused":
      return { text: "BLOCK · 0 MOVED", color: C.accent };
    case "contract_refused":
      return { text: "CONTRACT CAP · REFUSED", color: C.accent };
    default:
      return { text: e.result.toUpperCase(), color: C.dim };
  }
};

// Sums decimal display strings ("18", "0.5") and shows at most 2 decimals.
export const sumAmounts = (amounts: readonly string[]): string =>
  String(Number(amounts.reduce((acc, a) => acc + Number(a), 0).toFixed(2)));
