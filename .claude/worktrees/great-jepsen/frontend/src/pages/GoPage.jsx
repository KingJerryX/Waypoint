import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";

// #region agent log
function debugLog(message, data, hypothesisId) {
  fetch("http://127.0.0.1:7832/ingest/8a067dd9-fa67-459c-9257-28e916d33083", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "b65a9c" },
    body: JSON.stringify({ sessionId: "b65a9c", location: "GoPage.jsx", message, data: data || {}, hypothesisId: hypothesisId || "", timestamp: Date.now() }),
  }).catch(() => {});
}
// #endregion

export default function GoPage() {
  // #region agent log
  try { debugLog("GoPage render", { pathname: window.location.pathname }, "H4"); } catch (e) {}
  // #endregion
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const autoRun = searchParams.get("auto") === "1";
  const [manual, setManual] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const autoRunDone = useRef(false);
  const runAgentRef = useRef(null);
  runAgentRef.current = runAgent;

  useEffect(() => {
    if (!slug) {
      setLoadError(true);
      return;
    }
    fetch(`/api/manuals/${encodeURIComponent(slug)}`)
      .then((r) => {
        if (!r.ok) throw new Error("Not found");
        return r.json();
      })
      .then((m) => {
        // #region agent log
        debugLog("manual loaded", { slug, hasManual: !!m }, "H1");
        // #endregion
        setManual(m);
      })
      .catch(() => {
        // #region agent log
        debugLog("manual fetch failed", { slug }, "H1");
        // #endregion
        setLoadError(true);
      });
  }, [slug]);

  async function runAgent() {
    if (!manual) return;
    setRunning(true);
    setResult(null);
    try {
      const allowed = ["open_url", "get_page_state", "scroll_down", "done"];
      if (!manual.no_click) allowed.push("click", "type");
      const res = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: manual.url,
          task: manual.task,
          max_steps: manual.max_steps || 8,
          allowed_tools: allowed,
        }),
      });
      const data = await res.json();
      // #region agent log
      debugLog("run agent response", { ok: data.ok, hasError: !!data.error }, "H2");
      // #endregion
      setResult(data);
    } catch (e) {
      // #region agent log
      debugLog("run agent failed", { error: e.message }, "H2");
      // #endregion
      setResult({ ok: false, error: e.message || "Request failed." });
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    if (!manual || !autoRun || autoRunDone.current) return;
    autoRunDone.current = true;
    if (runAgentRef.current) runAgentRef.current();
  }, [manual, autoRun]);

  if (loadError) {
    return (
      <div className="wrap">
        <div className="section">
          <p style={{ color: "var(--error)", margin: 0 }}>
            This link is invalid or the manual was not found.
          </p>
        </div>
      </div>
    );
  }

  if (!manual) {
    return (
      <div className="wrap">
        <div className="section">
          <p className="loading">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <h1>{manual.title || "Run agent"}</h1>
      <p className="sub">{manual.task}</p>
      <div className="section">
        <h2>Run the agent</h2>
        <p className="meta">
          {manual.url} · max {manual.max_steps || 8} steps
        </p>
        <button type="button" onClick={runAgent} disabled={running}>
          {running ? "Running…" : "Run agent"}
        </button>
        {result && (
          <>
            {result.ok && result.answer ? (
              <div className="result-box success">{result.answer}</div>
            ) : (
              <div className="result-box error">
                {result.error || "Agent did not return an answer."}
              </div>
            )}
            {result.metrics && (
              <p className="meta">
                Steps: {result.metrics.steps_used} · Time: {result.metrics.total_time_s}s
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
