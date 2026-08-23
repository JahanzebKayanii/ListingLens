import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer,
} from "recharts";

const TABS = ["Performance prediction", "Bias language", "Market benchmark", "Skills found"];

const METRIC_LABELS = {
  salary_annual: "Salary",
  skill_count: "Skill count",
  readability_grade: "Readability grade",
  description_length: "Word count",
};

export default function ResultsPanel({ result }) {
  const [tab, setTab] = useState(TABS[0]);

  const summaryMetrics = [
    { label: "Skills detected", value: result.skills.length },
    { label: "Readability grade", value: result.readability_grade.toFixed(1) },
    { label: "Word count", value: result.word_count },
    { label: "Language lean", value: result.bias.lean_label },
  ];

  const chartData = result.prediction.contributions.map((c) => ({
    feature: c.feature,
    impact: Number(c.impact.toFixed(4)),
  }));

  return (
    <div className="results-panel">
      <div className="summary-row">
        {summaryMetrics.map((m) => (
          <div className="summary-metric" key={m.label}>
            <div className="summary-value">{m.value}</div>
            <div className="summary-label">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={`tab-btn ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === "Performance prediction" && (
          <div>
            <div className="risk-metric">
              <div className="summary-value">{Math.round(result.prediction.risk * 100)}%</div>
              <div className="summary-label">
                Underperformance risk - modeled probability this posting lands in the
                bottom 25% of application conversion rate for its industry/experience peer group
              </div>
            </div>
            <p className="chart-title">
              What's driving this prediction (red = raises risk, green = lowers it)
            </p>
            <ResponsiveContainer width="100%" height={380}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="feature" width={140} />
                <Tooltip />
                <Bar dataKey="impact">
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.impact > 0 ? "#d62728" : "#2ca02c"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {tab === "Bias language" && (
          <div className="bias-tab">
            <div className="bias-col">
              <strong>Masculine-coded words found</strong>
              <p>{result.bias.masculine_hits.join(", ") || "None"}</p>
            </div>
            <div className="bias-col">
              <strong>Feminine-coded words found</strong>
              <p>{result.bias.feminine_hits.join(", ") || "None"}</p>
            </div>
            <p className="hint">
              Based on research showing agentic/masculine-coded language in job posts
              correlates with fewer women applying, independent of the actual role.
            </p>
          </div>
        )}

        {tab === "Market benchmark" && (
          <div className="benchmark-tab">
            {Object.entries(result.benchmark).map(([key, val]) => (
              <div key={key} className="benchmark-row">
                <strong>{METRIC_LABELS[key] || key}</strong>{" "}
                {val ? (
                  <span>
                    {val.value} — {val.percentile.toFixed(0)}th percentile
                    (peer average: {val.group_mean.toFixed(2)}, n={val.group_n})
                  </span>
                ) : (
                  <span>not enough comparison data</span>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === "Skills found" && (
          <p>{result.skills.join(", ") || "No taxonomy skills detected"}</p>
        )}
      </div>
    </div>
  );
}
