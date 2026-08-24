import { useEffect, useState } from "react";
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

// what each SHAP feature actually measures, and which direction it
// typically pushes conversion - shown in the chart tooltip so "work_type_enc"
// reads as something a recruiter can actually act on
const FEATURE_INFO = {
  skill_count: {
    label: "Skills listed",
    text: "How many recognizable skills are named. Postings that state clear, specific skills tend to convert better than vague ones.",
  },
  readability_grade: {
    label: "Reading grade level",
    text: "US grade level needed to read this comfortably. Denser, jargon-heavy writing tends to correlate with lower conversion.",
  },
  readability_ease: {
    label: "Reading ease",
    text: "0-100 plain-English score (higher = easier). Low scores usually track with the same density problem as reading grade.",
  },
  bias_lean_score: {
    label: "Language lean",
    text: "Overall masculine vs. feminine-coded word balance. Strongly masculine-leaning language is associated with fewer applicants, especially fewer women.",
  },
  masculine_count: {
    label: "Masculine-coded words",
    text: "Count of agentic words (e.g. 'driven', 'competitive', 'dominate'). Research links heavier use to a narrower, more male-skewed applicant pool.",
  },
  feminine_count: {
    label: "Feminine-coded words",
    text: "Count of communal words (e.g. 'collaborative', 'supportive'). More balanced language generally correlates with broader appeal.",
  },
  description_length: {
    label: "Word count",
    text: "Total length of the posting. Longer, bloated postings tend to convert worse - candidates lose patience before applying.",
  },
  has_salary: {
    label: "Salary listed",
    text: "Whether a salary was provided at all. Listing one usually builds trust and improves conversion versus leaving it blank.",
  },
  remote_allowed: {
    label: "Remote allowed",
    text: "Whether the role allows remote work, which typically widens and improves the applicant pool.",
  },
  experience_level_enc: {
    label: "Experience level",
    text: "The stated seniority level, compared against how similar postings at that level typically perform.",
  },
  work_type_enc: {
    label: "Work type",
    text: "Full-time / contract / part-time / internship, compared against how that work type typically performs.",
  },
  industry_enc: {
    label: "Industry",
    text: "The posting's industry category, compared against typical conversion patterns for that industry.",
  },
};

function ShapTooltip({ active, payload, theme }) {
  if (!active || !payload?.length) return null;
  const { feature, impact } = payload[0].payload;
  const info = FEATURE_INFO[feature] || { label: feature, text: "" };
  const direction = impact > 0 ? "increased" : "decreased";
  const color = impact > 0 ? theme.danger : theme.good;

  return (
    <div style={{
      background: theme.tooltipBg, border: `1px solid ${theme.tooltipBorder}`,
      borderRadius: 8, padding: "0.6rem 0.75rem", maxWidth: 260, fontSize: 13,
    }}>
      <div style={{ fontWeight: 700, marginBottom: 2 }}>{info.label}</div>
      <div style={{ color, fontWeight: 600, marginBottom: 4 }}>
        {direction} risk by {Math.abs(impact).toFixed(3)}
      </div>
      <div style={{ color: theme.tick, lineHeight: 1.4 }}>{info.text}</div>
    </div>
  );
}

const CHART_THEME = {
  light: { grid: "#e4e1d9", tick: "#6f6b62", tooltipBg: "#ffffff", tooltipBorder: "#e4e1d9", danger: "#c4453a", good: "#2f8a5a" },
  dark: { grid: "#33373f", tick: "#a6a29a", tooltipBg: "#1c1f24", tooltipBorder: "#33373f", danger: "#ef6a5f", good: "#4bc582" },
};

function useColorScheme() {
  const query = "(prefers-color-scheme: dark)";
  const [isDark, setIsDark] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const listener = (e) => setIsDark(e.matches);
    mql.addEventListener("change", listener);
    return () => mql.removeEventListener("change", listener);
  }, []);
  return isDark ? "dark" : "light";
}

export default function ResultsPanel({ result }) {
  const [tab, setTab] = useState(TABS[0]);
  const theme = CHART_THEME[useColorScheme()];

  const summaryMetrics = [
    { label: "Skills detected", value: result.skills.length },
    { label: "Readability grade", value: result.readability_grade.toFixed(1) },
    { label: "Word count", value: result.word_count },
    { label: "Language lean", value: result.bias.lean_label },
  ];

  const chartData = result.prediction.contributions.map((c) => ({
    feature: c.feature,
    label: FEATURE_INFO[c.feature]?.label || c.feature,
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
                <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
                <XAxis type="number" tick={{ fill: theme.tick, fontSize: 12 }} stroke={theme.grid} />
                <YAxis type="category" dataKey="label" width={140} tick={{ fill: theme.tick, fontSize: 12 }} stroke={theme.grid} />
                <Tooltip content={<ShapTooltip theme={theme} />} cursor={{ fill: theme.grid, opacity: 0.3 }} />
                <Bar dataKey="impact" radius={[3, 3, 3, 3]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.impact > 0 ? theme.danger : theme.good} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {tab === "Bias language" && (
          <div>
            <div className="bias-tab">
              <div className="bias-col">
                <strong>Masculine-coded words found</strong>
                <p>{result.bias.masculine_hits.join(", ") || "None"}</p>
              </div>
              <div className="bias-col">
                <strong>Feminine-coded words found</strong>
                <p>{result.bias.feminine_hits.join(", ") || "None"}</p>
              </div>
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
