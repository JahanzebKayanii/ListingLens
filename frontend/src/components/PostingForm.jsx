export default function PostingForm({ metadata, values, onChange, onSubmit, loading }) {
  const set = (key) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    onChange({ ...values, [key]: val });
  };

  return (
    <div className="posting-form">
      <div className="form-left">
        <label htmlFor="posting-text">Job posting text</label>
        <textarea
          id="posting-text"
          rows={14}
          placeholder="Paste the full job description here..."
          value={values.text}
          onChange={set("text")}
        />
      </div>

      <div className="form-right">
        <h3>Context</h3>

        <label>Compare against industry</label>
        <select value={values.benchmark_industry} onChange={set("benchmark_industry")}>
          {metadata.industries.map((i) => (
            <option key={i} value={i}>{i}</option>
          ))}
        </select>

        <label>Compare against experience level</label>
        <select value={values.benchmark_experience} onChange={set("benchmark_experience")}>
          {metadata.experience_levels.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>

        <hr />
        <p className="hint">For the prediction model (not just benchmarking):</p>

        <label>This posting's experience level</label>
        <select value={values.experience_level} onChange={set("experience_level")}>
          {metadata.experience_levels.filter((e) => e !== "All").map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>

        <label>Work type</label>
        <select value={values.work_type} onChange={set("work_type")}>
          {metadata.work_types.map((w) => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>

        <label className="checkbox-label">
          <input type="checkbox" checked={values.remote_allowed} onChange={set("remote_allowed")} />
          Remote allowed
        </label>

        <label>Salary (0 if not listing one)</label>
        <input type="number" min="0" step="1000" value={values.salary} onChange={set("salary")} />

        <label>Pay period</label>
        <select value={values.pay_period} onChange={set("pay_period")}>
          <option>Yearly</option>
          <option>Hourly</option>
          <option>Monthly</option>
        </select>
      </div>

      <button className="analyze-btn" onClick={onSubmit} disabled={loading || !values.text.trim()}>
        {loading ? "Analyzing..." : "Analyze posting"}
      </button>
    </div>
  );
}
