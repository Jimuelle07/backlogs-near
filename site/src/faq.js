// FAQ: short, factual answers for people, search engines and AI answer engines. The same list
// renders the #faq section and the FAQPage JSON-LD (scripts/prerender.mjs), so they never differ.
// Every figure comes from config.js or docs/results/results.json; keep wording in line with the README.
import results from "../../docs/results/results.json";
import { DAILY_CAP, PER_PAYMENT_CAP, PROJECT_NAME } from "./config.js";
import { FROZEN_Q_HAT, headline } from "./results.js";

const top = headline(results);
const pct = (n) => `${Number(n.toFixed(2))}%`;

export const FAQ = [
  {
    q: `What is ${PROJECT_NAME}?`,
    a: `${PROJECT_NAME} is a payment firewall for AI agents on NEAR. The agent holds only a function-call key that can ask a Guardian contract for a payment. The contract holds the funds, pauses each request, and pays only after a checker running off the agent's host returns allow.`,
  },
  {
    q: "How does it stop prompt-injection payments?",
    a: "Each payment request runs a checker: policy rules (the amount must match the request or invoice), an injection classifier on everything the agent read, and counterparty signals such as account age and lookalike distance to known payees. TypeSafe Jev fuses these signals into allow, hold or block.",
  },
  {
    q: "When is a payment held or blocked?",
    a: `A payment is held when Jev's "unusual" score is above the conformal threshold (q̂ ${FROZEN_Q_HAT}, ε = 5%) or when a non-Jev detector raises an attack flag. It is blocked only when the score is above the threshold and two attack signals from different detectors agree, at most one of them from Jev. Thresholds live in the checker's configuration, not in prompts.`,
  },
  {
    q: "What does NEAR do in this design?",
    a: `NEAR holds the funds in the Guardian contract, limits the agent's key to one method, pauses each request with yield and resume, pays only on an exact match of receiver, token, amount and request id, enforces hard caps (${PER_PAYMENT_CAP} tUSDC per payment, ${DAILY_CAP} tUSDC per UTC day) and writes an on-chain receipt for every payment.`,
  },
  {
    q: "Does a human approve payments?",
    a: "No. Allowed payments are paid at once, unless the amount is above the payee's budget (a new payee starts at 20 tUSDC), in which case they wait like a hold. Held payments wait in escrow for a window set by the amount (10 minutes under 20 tUSDC, 1 hour up to 100, 6 hours above) and are then released by a release_held call, which any account can send. The owner can cancel a hold. No AI decides an amount.",
  },
  {
    q: "How well does it work?",
    a: top
      ? `On ${results.benign_total} benign and ${results.attack_total} attack payments across six attack families, Jev fusion with the conformal threshold missed ${pct(top.best.missed_attacks_pct)} of attacks (${pct(top.base.missed_attacks_pct)} with no defense), with ${pct(top.best.false_blocks_pct)} false blocks and ${pct(top.best.false_holds_pct)} false holds. The false-hold figure is in-sample and above the 5% target. Fake-invoice and memory-poisoning attacks are the weakest families.`
      : "See the Results section.",
  },
  {
    q: "What are the limits?",
    a: `Detection covers the six evaluated attack families; new or adaptive attacks are bounded only by the hard caps in contract code. The masked re-run (MELON) and a re-check during the hold window are not built. The false-hold bound assumes live payments look like the calibration set.`,
  },
  {
    q: "Is it live on mainnet?",
    a: "No. It is a NEAR HACKATHON 2026 build that runs on NEAR testnet with a mock tUSDC token (6 decimals). The receipts panel on this page reads the testnet Guardian live.",
  },
  {
    q: "Can I try it without keys?",
    a: "Yes. From the repository, build the checker with cargo build -p checker --release, then in agent/ run uv sync and uv run firewall-demo --scenario benign-hosting, then the attack-morse-lookalike scenario. The dry-run needs no keys and no funds.",
  },
];

export function faqJsonLd() {
  return {
    "@type": "FAQPage",
    mainEntity: FAQ.map(({ q, a }) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
  };
}
