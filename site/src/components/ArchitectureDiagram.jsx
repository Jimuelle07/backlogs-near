// D2: payment path, agent → Guardian → checker (TEE) → verdict → transfer + receipt.
// Desktop: one SVG. Phones: the same path as a stacked list (CSS switches at 760px).

// `at` is the box's place in the scroll-driven build (motion.js lights steps in order).
function Box({ x, y, w, h, title, sub, tone = "", at, children }) {
  return (
    <g className={`pp-box ${tone}`} data-at={at}>
      <rect x={x} y={y} width={w} height={h} rx="8" />
      <text className="pp-title" x={x + 14} y={y + 26}>{title}</text>
      {sub && <text className="pp-sub" x={x + 14} y={y + 46}>{sub}</text>}
      {children}
    </g>
  );
}

// `step` orders the travelling pulse along the payment path (see .pp-flow in styles.css).
function Flow({ d, step, at }) {
  return (
    <g aria-hidden="true" className="pp-flowg" data-flow-at={at} style={{ "--s": step }}>
      <path className="pp-march" d={d} />
      <path className="pp-flow" d={d} pathLength="1" />
    </g>
  );
}

function Arrow({ d, label, lx, ly, anchor = "middle", tone = "", step, at }) {
  return (
    <>
      <g className={`pp-arrow ${tone}`} data-at={at}>
        <path d={d} pathLength="1" markerEnd="url(#pp-head)" />
        {label && <text className="pp-label" x={lx} y={ly} textAnchor={anchor}>{label}</text>}
      </g>
      {step !== undefined && <Flow d={d} step={step} at={at} />}
    </>
  );
}

const CHECKS = [
  ["Policy rules", "allowlist · amount match", 615, 96, ""],
  ["Injection classifier", "scores what the agent read", 800, 96, ""],
  ["Counterparty", "age · lookalike · history", 615, 150, ""],
  ["Masked re-run", "planned", 800, 150, "planned"],
];

function DesktopDiagram() {
  return (
    <svg className="pp-svg" viewBox="0 0 1000 520" role="img" aria-labelledby="pp-t pp-d">
      <title id="pp-t">Payment path</title>
      <desc id="pp-d">
        The agent can only call request_payment on the Guardian contract. The Guardian holds the funds, pauses the
        payment and asks the checker in an OutLayer TEE for a verdict. Four checks feed Jev, which returns allow, hold
        or block. The Guardian then pays, escrows or refuses, and writes an on-chain receipt.
      </desc>
      <defs>
        <marker id="pp-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" className="pp-headfill" />
        </marker>
      </defs>

      {/* Inputs and agent */}
      <Box x={20} y={30} w={180} h={70} title="What the agent reads" sub="request + untrusted text" tone="warn" at={0} />
      <Arrow d="M110 100 V146" step={0} at={1} />
      <Box x={20} y={150} w={180} h={110} title="Agent" sub="Python · LLM tool calls" at={1}>
        <text className="pp-chip" x={34} y={222}>function-call key:</text>
        <text className="pp-chip" x={34} y={240}>request_payment only</text>
      </Box>

      {/* Agent → Guardian */}
      <Arrow d="M200 205 H326" label="request_payment" lx={263} ly={194} step={1} at={2} />
      <Box x={330} y={130} w={190} h={150} title="Guardian contract" sub="holds the tUSDC" tone="key" at={2}>
        <text className="pp-sub" x={344} y={226}>caps 200 / payment</text>
        <text className="pp-sub" x={344} y={246}>500 / day, in code</text>
      </Box>

      {/* Guardian ⇄ checker */}
      <Arrow d="M520 180 H596" label="yield" lx={558} ly={169} step={2} at={3} />
      <Arrow d="M600 240 H524" label="verdict" lx={562} ly={262} step={5} at={6} />

      {/* Checker in the TEE */}
      <g className="pp-tee" data-at={3}>
        <rect x={600} y={40} width={380} height={310} rx="10" />
        <text className="pp-title" x={614} y={66}>Checker WASM · OutLayer TEE (Intel TDX)</text>
      </g>
      {CHECKS.map(([t, s, x, y, tone]) => (
        <g key={t} className={`pp-check ${tone}`} data-at={3}>
          <rect x={x} y={y} width={165} height={44} rx="6" />
          <text className="pp-ct" x={x + 10} y={y + 19}>{t}</text>
          <text className="pp-cs" x={x + 10} y={y + 35}>{s}</text>
        </g>
      ))}
      <Arrow d="M790 196 V222" step={3} at={4} />
      <g className="pp-jev" data-at={4}>
        <rect x={615} y={226} width={350} height={46} rx="6" />
        <text className="pp-ct" x={629} y={246}>Jev fusion</text>
        <text className="pp-cs" x={629} y={262}>calibrated judgments; thresholds stay in checker config</text>
      </g>
      <Arrow d="M790 272 V296" step={4} at={5} />
      <g className="pp-verdict" data-at={5}>
        <rect x={700} y={300} width={180} height={34} rx="17" />
        <text x={790} y={322} textAnchor="middle">allow · hold · block</text>
      </g>
      <text className="pp-out" data-at={3} x={980} y={380} textAnchor="end">Calls out, not attested:</text>
      <text className="pp-out" data-at={3} x={980} y={398} textAnchor="end">Jev API · NEAR AI Cloud · classifier host</text>

      {/* Outcomes: Guardian fans out to allow / hold / block */}
      <g className="pp-arrow" data-at={7}><path d="M425 280 V324 M110 324 H530" pathLength="1" /></g>
      <Flow d="M425 280 V324 M110 324 H530" step={6} at={7} />
      <Arrow d="M110 324 V364" step={7} at={7} />
      <Arrow d="M320 324 V364" step={7} at={7} />
      <Arrow d="M530 324 V364" step={7} at={7} />
      <Box x={20} y={368} w={180} h={66} title="Allow" sub="ft_transfer, pays now" tone="allow" at={7} />
      <Box x={230} y={368} w={180} h={66} title="Hold" sub="escrow 10 min – 6 h" tone="hold" at={7} />
      <Box x={440} y={368} w={180} h={66} title="Block" sub="refused, nothing moves" tone="block" at={7} />
      <g className="pp-receipt" data-at={8}>
        <rect x={20} y={456} width={600} height={44} rx="8" />
        <text x={36} y={483}>On-chain receipt: outcome · reasons · hashes · checker version</text>
      </g>
    </svg>
  );
}

const STEPS = [
  ["Agent", "Reads the user's request and untrusted text. Its key can call request_payment, nothing else."],
  ["Guardian contract", "Holds the tUSDC, checks the caps, pauses the payment and asks for a verdict."],
  ["Checker in a TEE", "Policy, injection and counterparty checks (masked re-run planned) run inside OutLayer on Intel TDX."],
  ["Jev fusion", "Turns the signals into allow, hold or block. Thresholds live in checker config."],
  ["Guardian acts", "Allow pays now, hold escrows and re-checks, block refuses. Every outcome writes an on-chain receipt."],
];

function MobileDiagram() {
  return (
    <ol className="pp-list" aria-label="Payment path">
      {STEPS.map(([t, d], i) => (
        <li key={t} className={i === 1 || i === 2 ? "key" : ""}>
          <b>{t}</b>
          <span>{d}</span>
        </li>
      ))}
    </ol>
  );
}

export function ArchitectureDiagram() {
  return (
    <figure className="pp">
      <DesktopDiagram />
      <MobileDiagram />
      <figcaption>
        The agent never holds a key that can move money. Only the Guardian pays, and only on a verdict that matches the
        exact receiver, token, amount and request id.
      </figcaption>
    </figure>
  );
}
