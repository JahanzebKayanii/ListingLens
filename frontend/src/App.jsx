import { useEffect, useState } from "react";
import { getMetadata, analyzePosting } from "./api";
import PostingForm from "./components/PostingForm";
import ResultsPanel from "./components/ResultsPanel";
import "./App.css";

const DEFAULT_VALUES = {
  text: "",
  benchmark_industry: "All",
  benchmark_experience: "All",
  experience_level: "",
  work_type: "",
  remote_allowed: false,
  salary: 0,
  pay_period: "Yearly",
};

export default function App() {
  const [metadata, setMetadata] = useState(null);
  const [metaError, setMetaError] = useState(null);
  const [values, setValues] = useState(DEFAULT_VALUES);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMetadata()
      .then((data) => {
        setMetadata(data);
        setValues((v) => ({
          ...v,
          experience_level: data.experience_levels.find((e) => e !== "All") || "",
          work_type: data.work_types[0] || "",
        }));
      })
      .catch((e) => setMetaError(e.message));
  }, []);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = { ...values, salary: Number(values.salary) || null };
      const data = await analyzePosting(payload);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (metaError) {
    return (
      <div className="app-shell">
        <p className="error-banner">
          Couldn't reach the API at localhost:8000 - is it running? ({metaError})
        </p>
      </div>
    );
  }

  if (!metadata) {
    return <div className="app-shell">Loading...</div>;
  }

  return (
    <div className="app-shell">
      <header>
        <div className="brand">
          <span className="brand-mark">🔍</span>
          <h1>ListingLens</h1>
        </div>
        <p>Paste a job posting and see how it will actually land with candidates.</p>
      </header>

      <PostingForm
        metadata={metadata}
        values={values}
        onChange={setValues}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && <p className="error-banner">{error}</p>}
      {result && <ResultsPanel result={result} />}
    </div>
  );
}
