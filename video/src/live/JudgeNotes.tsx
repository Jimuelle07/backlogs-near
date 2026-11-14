import type React from "react";
import { AbsoluteFill } from "remotion";
import { Reveal } from "../Reveal";
import { C, mono, sans } from "../theme";
import type { RunData } from "./types";

export const JudgeNotes: React.FC<{ readonly data: RunData }> = ({ data }) => {
  const { caps } = data;
  const ecl = data.events.filter((e) => e.side === "eclipse");
  const capRefused = ecl.find((e) => e.result === "contract_refused");
  const misses = ecl.filter((e) => e.result === "would_pay" && e.to_attacker);
  const bullets: string[] = [
    "Same proposals, same keys: the only difference between the two takes is Eclipse.",
    `No AI judges the amount. The verdict binds receiver, token, exact amount and request_id; caps live in contract code: ${caps.per_payment} per payment, ${caps.daily} per day, ${caps.new_payee} for a new payee.` +
      (capRefused ? ` The ${capRefused.amount} tUSDC drain was refused by the cap before any model ran.` : ""),
    `No human step: allow, hold (escrow, owner can cancel) or block` +
      (data.check_s ? `, in ${data.check_s.median} s median per payment (4 checks at once on a local CPU classifier).` : "."),
    "Jev's probabilities stay in the owner's off-chain log; the agent and the chain see only the verdict and reason codes.",
    ...misses.map(
      (m) => `Missed: ${m.scenario}, ${m.amount} tUSDC to a new payee — bounded by the ${caps.new_payee} tUSDC new-payee budget.`,
    ),
    "Jev's scores vary between runs. Dry-run chain; one take per side.",
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: C.ground, fontFamily: sans, padding: "80px 140px", justifyContent: "center", color: C.text }}>
      <Reveal delay={0}>
        <div style={{ fontSize: 56, fontWeight: 700 }}>What to check</div>
      </Reveal>
      {bullets.map((b, i) => (
        <Reveal key={b} delay={18 + i * 40} style={{ display: "flex", gap: 22, marginTop: 26, fontSize: 29, lineHeight: 1.35 }}>
          <div style={{ fontFamily: mono, color: C.accent, minWidth: 34 }}>{i + 1}.</div>
          <div style={{ color: b.startsWith("Missed") ? C.hold : C.text }}>{b}</div>
        </Reveal>
      ))}
      <Reveal delay={18 + bullets.length * 40 + 20} style={{ marginTop: 48, fontSize: 30, fontWeight: 600, color: C.accent }}>
        Eclipse — steps in front of the bad payment, stays in the background otherwise.
      </Reveal>
    </AbsoluteFill>
  );
};
