import results from "../../../docs/results/results.json";
import redteam from "../../../docs/results/redteam-results.json";
import {
  DAILY_CAP, PER_PAYMENT_CAP,
} from "../config.js";
import {
  FROZEN_Q_HAT, familyRows, formatCalls, formatResultNumber, headline, mapResultsRows, redteamRow,
} from "../results.js";

const resultRows = mapResultsRows(results);
const redteamResult = redteamRow(redteam);
const families = familyRows(results);
const top = headline(results);
const SERIES = [
  { key: "missedAttacksPct", label: "Missed attacks", className: "results-missed" },
  { key: "falseBlocksPct", label: "False blocks", className: "results-blocks" },
];

// Compact chart: configuration names in a left column, two thin bars per row beside them.
function ResultsChart({ rows }) {
  const labelRight = 196;
  const left = 208;
  const plotWidth = 340;
  const groupHeight = 38;
  const top = 34;
  const bottom = top + rows.length * groupHeight;
  const ticks = [0, 25, 50, 75, 100]; // Percentage axis, not observed results.

  return (
    <figure className="results-chart" aria-labelledby="results-chart-title">
      <figcaption id="results-chart-title">Missed attacks and false blocks by configuration</figcaption>
      <ul className="results-legend" aria-label="Chart legend">
        {SERIES.map((series) => (
          <li key={series.key}><span className={series.className} aria-hidden="true" />{series.label}</li>
        ))}
      </ul>
      <svg viewBox={`0 0 600 ${bottom + 44}`} role="img" aria-labelledby="results-svg-title results-svg-desc">
        <title id="results-svg-title">Missed attacks and false blocks (%)</title>
        <desc id="results-svg-desc">Grouped horizontal bars for each configuration. Exact values are in the results table above.</desc>
        <text x={labelRight} y="18" textAnchor="end" className="results-axis-title">Configuration</text>
        {ticks.map((tick) => {
          const x = left + (tick / 100) * plotWidth;
          return (
            <g key={tick}>
              <line x1={x} x2={x} y1={top - 6} y2={bottom} className="results-gridline" />
              <text x={x} y={bottom + 18} textAnchor="middle">{tick}</text>
            </g>
          );
        })}
        {rows.map((row, index) => {
          const y = top + index * groupHeight;
          return (
            <g key={row.configuration}>
              <text x={labelRight} y={y + 17} textAnchor="end" className="results-config-label">{row.configuration}</text>
              {SERIES.map((series, seriesIndex) => {
                const value = row[series.key];
                const width = (value / 100) * plotWidth;
                const barY = y + 5 + seriesIndex * 13;
                return (
                  <g key={series.key}>
                    <rect x={left} y={barY} width={width} height="10" rx="1.5" className={series.className}>
                      <title>{`${row.configuration}: ${series.label} ${formatResultNumber(value)}%`}</title>
                    </rect>
                    <text x={left + width + 6} y={barY + 9} className="results-val">{formatResultNumber(value)}</text>
                  </g>
                );
              })}
            </g>
          );
        })}
        <line x1={left} x2={left + plotWidth} y1={bottom} y2={bottom} className="results-axis" />
        <text x={left + plotWidth / 2} y={bottom + 38} textAnchor="middle" className="results-axis-title">Rate (%)</text>
      </svg>
      {/* Phones: the same numbers as a plain bar list (the SVG text gets too small). */}
      <ul className="rchart-list" aria-hidden="true">
        {rows.map((row) => (
          <li key={row.configuration}>
            <span className="rl-name">{row.configuration}</span>
            {SERIES.map((series) => (
              <span className="rl-bar" key={series.key}>
                <i className={series.className} style={{ width: `${row[series.key]}%` }} />
                <b>{formatResultNumber(row[series.key])}</b>
              </span>
            ))}
          </li>
        ))}
      </ul>
    </figure>
  );
}

export function ResultsSection({ rows = resultRows }) {
  return (
    <section className="sec" id="results" aria-labelledby="results-title">
      <div className="head2">
        <div className="l">
          <h2 id="results-title">Measured, not promised</h2>
        </div>
        <p>
          Every check on and off over {results.benign_total} benign and {results.attack_total} attack payments (six attack
          families), decided by live Jev calls with the injection classifier on. Read from{" "}
          <code className="ic">docs/results/results.json</code>.
        </p>
      </div>
      {top && (
        <div className="rstats">
          <div className="rstat">
            <span className="k">Missed attacks</span>
            <strong>{formatResultNumber(top.best.missed_attacks_pct)}%</strong>
            <small>vs {formatResultNumber(top.base.missed_attacks_pct)}% with no defense</small>
          </div>
          <div className="rstat">
            <span className="k">False blocks</span>
            <strong>{formatResultNumber(top.best.false_blocks_pct)}%</strong>
            <small>benign payments refused</small>
          </div>
          <div className="rstat">
            <span className="k">False holds</span>
            <strong>{formatResultNumber(top.best.false_holds_pct)}%</strong>
            <small>target ε = 5%; in-sample</small>
          </div>
        </div>
      )}
      <div className="tablewrap results-table-wrap" role="region" aria-label="Results table; scroll horizontally for all metrics" tabIndex={0}>
        <table className="results-table">
          <caption className="sr-only">Results by configuration</caption>
          <thead>
            <tr>
              <th scope="col">Configuration</th>
              <th scope="col">False holds (%)</th>
              <th scope="col">False blocks (%)</th>
              <th scope="col">Missed attacks (%)</th>
              <th scope="col">Median latency (ms)</th>
              <th scope="col">Per payment</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.configuration}>
                <th scope="row"><span className="results-config">{row.configuration}</span><span className="results-description">{row.label}</span></th>
                <td className="num" data-label="False holds (%)">{formatResultNumber(row.falseHoldsPct)}</td>
                <td className="num" data-label="False blocks (%)">{formatResultNumber(row.falseBlocksPct)}</td>
                <td className="num" data-label="Missed attacks (%)">{formatResultNumber(row.missedAttacksPct)}</td>
                <td className="num" data-label="Median latency (ms)">{formatResultNumber(row.medianLatencyMs)}</td>
                <td className="num" data-label="Per payment">{formatCalls(row)}</td>
              </tr>
            ))}
            <tr className="results-extra">
              <th scope="row"><span className="results-config">redteam</span><span className="results-description">Red-team round, {redteamResult.total} attacks, conformal row</span></th>
              <td className="num" data-label="False holds (%)">n/a</td>
              <td className="num" data-label="False blocks (%)">n/a</td>
              <td className="num" data-label="Missed attacks (%)">{formatResultNumber(redteamResult.missedPct)} <small>({redteamResult.held} held, {redteamResult.blocked} blocked)</small></td>
              <td className="num" data-label="Median latency (ms)">{formatResultNumber(redteamResult.medianMs)}</td>
              <td className="num" data-label="Per payment">{formatCalls(redteamResult)}</td>
            </tr>
            <tr className="results-extra">
              <th scope="row"><span className="results-config">melon</span><span className="results-description">Masked re-run (MELON) only</span></th>
              <td className="num" colSpan={5} data-label="Status">Not built (cut list)</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="rgrid">
      <ResultsChart rows={rows} />
      <div className="rside">
      <div className="families">
        <h3>Attacks caught, by family <small>cascade row, q̂ {FROZEN_Q_HAT}</small></h3>
        <ul>
          {families.map((f) => (
            <li key={f.family}>
              <span className="fam-name">{f.label}</span>
              <span className="fam-bar" aria-hidden="true"><span style={{ width: `${f.caughtPct}%` }} /></span>
              <span className="fam-val">{f.caught}/{f.total}</span>
            </li>
          ))}
        </ul>
      </div>
      <ul className="note caveats">
        <li>
          The false-hold bound assumes live payments look like the calibration set (exchangeability). The{" "}
          {top ? formatResultNumber(top.best.false_holds_pct) : "—"}% is measured on the same benign set used to calibrate
          (in-sample) and is above the 5% target.
        </li>
        <li>
          Detection covers the six evaluated attack families. Against new or adaptive attacks, the loss is bounded by the
          hard caps in contract code: {PER_PAYMENT_CAP} tUSDC per payment, and {DAILY_CAP} tUSDC committed per UTC request
          day. Payouts on one day can also include holds committed the day before.
        </li>
        <li>
          Latency includes the injection classifier running on a local CPU. Cost is unpriced, so the table shows calls per
          payment. More sets (external held-out, PaySim, BEC) are in the README Results section.
        </li>
      </ul>
      </div>
      </div>
    </section>
  );
}
