// D2: payment path, agent → Guardian → checker (TEE) → verdict → transfer + receipt.
// Desktop: one SVG. Phones: the same path as a stacked list (CSS switches at 760px).

function Box({ x, y, w, h, title, sub, tone = "", children }) {
  return (
    <g className={`ad-box ${tone}`}>
      <rect x={x} y={y} width={w} height={h} rx="8" />
      <text className="ad-title" x={x + 14} y={y + 26}>{title}</text>
      {sub && <text className="ad-sub" x={x + 14} y={y + 46}>{sub}</text>}
      {children}
    </g>
  );
}

function Arrow({ d, label, lx, ly, anchor = "middle", tone = "" }) {
  return (
    <g className={`ad-arrow ${tone}`}>
      <path d={d} markerEnd="url(#ad-head)" />
      {label && <text className="ad-label" x={lx} y={ly} textAnchor={anchor}>{label}</text>}
    </g>
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
    <svg className="ad-svg" viewBox="0 0 1000 520" role="img" aria-labelledby="ad-t ad-d">
      <title id="ad-t">Payment path</title>
      <desc id="ad-d">
        The agent can only call request_payment on the Guardian contract. The Guardian holds the funds, pauses the
        payment and asks the checker in an OutLayer TEE for a verdict. Four checks feed Jev, which returns allow, hold
        or block. The Guardian then pays, escrows or refuses, and writes an on-chain receipt.
      </desc>
      <defs>
        <marker id="ad-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" className="ad-headfill" />
        </marker>
      </defs>

      {/* Inputs and agent */}
      <Box x={20} y={30} w={180} h={70} title="What the agent reads" sub="request + untrusted text" tone="warn" />
      <Arrow d="M110 100 V146" />
      <Box x={20} y={150} w={180} h={110} title="Agent" sub="Python · LLM tool calls">
        <text className="ad-chip" x={34} y={222}>function-call key:</text>
        <text className="ad-chip" x={34} y={240}>request_payment only</text>
      </Box>

      {/* Agent → Guardian */}
      <Arrow d="M200 205 H326" label="request_payment" lx={263} ly={194} />
      <Box x={330} y={130} w={190} h={150} title="Guardian contract" sub="holds the tUSDC" tone="key">
        <text className="ad-sub" x={344} y={226}>caps 200 / payment</text>
        <text className="ad-sub" x={344} y={246}>500 / day, in code</text>
      </Box>

      {/* Guardian ⇄ checker */}
      <Arrow d="M520 180 H596" label="yield" lx={558} ly={169} />
      <Arrow d="M600 240 H524" label="verdict" lx={562} ly={262} />

      {/* Checker in the TEE */}
      <g className="ad-tee">
        <rect x={600} y={40} width={380} height={310} rx="10" />
        <text className="ad-title" x={614} y={66}>Checker WASM · OutLayer TEE (Intel TDX)</text>
      </g>
      {CHECKS.map(([t, s, x, y, tone]) => (
        <g key={t} className={`ad-check ${tone}`}>
          <rect x={x} y={y} width={165} height={44} rx="6" />
          <text className="ad-ct" x={x + 10} y={y + 19}>{t}</text>
          <text className="ad-cs" x={x + 10} y={y + 35}>{s}</text>
        </g>
      ))}
      <Arrow d="M790 196 V222" />
      <g className="ad-jev">
        <rect x={615} y={226} width={350} height={46} rx="6" />
        <text className="ad-ct" x={629} y={246}>Jev fusion</text>
        <text className="ad-cs" x={629} y={262}>calibrated judgments; thresholds stay in checker config</text>
      </g>
      <Arrow d="M790 272 V296" />
      <g className="ad-verdict">
        <rect x={700} y={300} width={180} height={34} rx="17" />
        <text x={790} y={322} textAnchor="middle">allow · hold · block</text>
      </g>
      <text className="ad-out" x={980} y={380} textAnchor="end">Calls out, not attested:</text>
      <text className="ad-out" x={980} y={398} textAnchor="end">Jev API · NEAR AI Cloud · classifier host</text>

      {/* Outcomes: Guardian fans out to allow / hold / block */}
      <g className="ad-arrow"><path d="M425 280 V324 M110 324 H530" /></g>
      <Arrow d="M110 324 V364" />
      <Arrow d="M320 324 V364" />
      <Arrow d="M530 324 V364" />
      <Box x={20} y={368} w={180} h={66} title="Allow" sub="ft_transfer, pays now" tone="allow" />
      <Box x={230} y={368} w={180} h={66} title="Hold" sub="escrow 10 min – 6 h" tone="hold" />
      <Box x={440} y={368} w={180} h={66} title="Block" sub="refused, nothing moves" tone="block" />
      <g className="ad-receipt">
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
    <ol className="ad-list" aria-label="Payment path">
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
    <figure className="ad">
      <DesktopDiagram />
      <MobileDiagram />
      <figcaption>
        The agent never holds a key that can move money. Only the Guardian pays, and only on a verdict that matches the
        exact receiver, token, amount and request id.
      </figcaption>
    </figure>
  );
}
