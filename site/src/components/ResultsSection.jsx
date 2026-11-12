import results from "../../../schemas/examples/results.json";
import { formatResultNumber, mapResultsRows } from "../results.js";

const sampleRows = mapResultsRows(results);
const SERIES = [
  { key: "missedAttacksPct", label: "Missed attacks", className: "results-missed" },
  { key: "falseBlocksPct", label: "False blocks", className: "results-blocks" },
];

function ResultsChart({ rows }) {
  const left = 36;
  const plotWidth = 264;
  const groupHeight = 90;
  const bottom = rows.length * groupHeight + 42;
  const ticks = [0, 25, 50, 75, 100]; // Percentage axis, not observed results.

  return (
    <figure className="results-chart" aria-labelledby="results-chart-title">
      <figcaption id="results-chart-title">Missed attacks and false blocks by configuration</figcaption>
      <ul className="results-legend" aria-label="Chart legend">
        {SERIES.map((series) => (
          <li key={series.key}><span className={series.className} aria-hidden="true" />{series.label}</li>
        ))}
      </ul>
      <svg viewBox={`0 0 360 ${bottom + 60}`} role="img" aria-labelledby="results-svg-title results-svg-desc">
        <title id="results-svg-title">Missed attacks and false blocks (%)</title>
        <desc id="results-svg-desc">Grouped horizontal bars for each configuration. Exact values and descriptions are in the results table above.</desc>
        <text x={left} y="18" className="results-axis-title">Configuration</text>
        {ticks.map((tick) => {
          const x = left + (tick / 100) * plotWidth;
          return (
            <g key={tick}>
              <line x1={x} x2={x} y1="32" y2={bottom} className="results-gridline" />
              <text x={x} y={bottom + 22} textAnchor="middle">{tick}</text>
            </g>
          );
        })}
        {rows.map((row, index) => {
          const y = 52 + index * groupHeight;
          return (
            <g key={row.configuration}>
              <text x={left} y={y} className="results-config-label">{row.configuration}</text>
              {SERIES.map((series, seriesIndex) => {
                const value = row[series.key];
                const width = (value / 100) * plotWidth;
                const barY = y + 12 + seriesIndex * 24;
                return (
                  <g key={series.key}>
                    <rect x={left} y={barY} width={width} height="14" className={series.className}>
                      <title>{`${row.configuration}: ${series.label} ${formatResultNumber(value)}%`}</title>
                    </rect>
                    <text x={left + width + 6} y={barY + 12}>{formatResultNumber(value)}</text>
                  </g>
                );
              })}
            </g>
          );
        })}
        <line x1={left} x2={left + plotWidth} y1={bottom} y2={bottom} className="results-axis" />
        <text x={left + plotWidth / 2} y={bottom + 48} textAnchor="middle" className="results-axis-title">Rate (%)</text>
      </svg>
    </figure>
  );
}

export function ResultsSection({ rows = sampleRows }) {
  return (
    <section className="sec" id="results" aria-labelledby="results-title">
      <div className="head2">
        <div className="l">
          <span className="kicker">Results</span>
          <h2 id="results-title">Measured, not promised</h2>
          <span className="tag">Sample data</span>
        </div>
        <p>Illustrative configurations from the sample evaluation file. These are sample values, not measured live results.</p>
      </div>
      <div className="tablewrap results-table-wrap" role="region" aria-label="Sample results table; scroll horizontally for all metrics" tabIndex={0}>
        <table className="results-table">
          <caption className="sr-only">Sample data: results by configuration</caption>
          <thead>
            <tr>
              <th scope="col">Configuration</th>
              <th scope="col">False holds (%)</th>
              <th scope="col">False blocks (%)</th>
              <th scope="col">Missed attacks (%)</th>
              <th scope="col">Median latency (ms)</th>
              <th scope="col">Cost per payment (USD)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.configuration}>
                <th scope="row"><span className="results-config">{row.configuration}</span><span className="results-description">{row.description}</span></th>
                <td className="num">{formatResultNumber(row.falseHoldsPct)}</td>
                <td className="num">{formatResultNumber(row.falseBlocksPct)}</td>
                <td className="num">{formatResultNumber(row.missedAttacksPct)}</td>
                <td className="num">{formatResultNumber(row.medianLatencyMs)}</td>
                <td className="num">{formatResultNumber(row.costPerPaymentUsd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ResultsChart rows={rows} />
      <p className="note">
        The false-hold bound holds only while an agent behaves like its calibration history (exchangeability).
        Attack detection results cover known attack families. The hard cap holds regardless.
      </p>
    </section>
  );
}
