import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";

const TERMINAL = ["completed", "failed", "terminated", "timed_out", "canceled"];

function StatusPill({ status }) {
  const running = status === "running" || status === "queued" || status === "created";
  return (
    <span className={`status-pill status-${status}`}>
      {running && <span className="pulse" />}
      {status}
    </span>
  );
}

function ScreenshotViewer({ screenshots, status }) {
  const latest = screenshots?.length ? screenshots[screenshots.length - 1] : null;
  return (
    <div className="screenshot-viewer">
      {latest ? (
        <>
          <img src={latest} alt="Browser screenshot" />
          {screenshots.length > 1 && (
            <span className="screenshot-count">frame {screenshots.length}</span>
          )}
        </>
      ) : (
        <div className="screenshot-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
          </svg>
          <span>{status === "running" ? "Starting browser…" : "Ready to run"}</span>
        </div>
      )}
    </div>
  );
}

export default function GoPage() {
  const { slug } = useParams();
  const [manual, setManual] = useState(null);
  const [loadError, setLoadError] = useState(false);

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState(null);
  const [screenshots, setScreenshots] = useState([]);
  const [output, setOutput] = useState(null);
  const [recordingUrl, setRecordingUrl] = useState(null);
  const [appUrl, setAppUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) { setLoadError(true); return; }
    fetch(`/api/manuals/${encodeURIComponent(slug)}`)
      .then(r => { if (!r.ok) throw new Error("Not found"); return r.json(); })
      .then(setManual)
      .catch(() => setLoadError(true));
  }, [slug]);

  const runAutomation = async () => {
    if (!manual) return;
    setRunning(true);
    setStatus("running");
    setScreenshots([]);
    setOutput(null);
    setRecordingUrl(null);
    setAppUrl(null);
    setError(null);

    try {
      const response = await fetch("/api/run/local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: manual.task,
          url: manual.url || undefined,
          max_steps: manual.max_steps || 15,
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to start task");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "status") {
              setStatus(event.status);
            } else if (event.type === "screenshot") {
              setStatus("running");
              setScreenshots(prev => [...prev, `data:image/png;base64,${event.data}`]);
            } else if (event.type === "done") {
              setStatus(event.ok ? "completed" : "failed");
              setRunning(false);
              if (event.ok) {
                setOutput(event.answer || "Task completed successfully.");
              } else {
                setError(event.error || "Task failed.");
              }
            } else if (event.type === "error") {
              setRunning(false);
              setStatus("failed");
              setError(event.error);
            }
          } catch {}
        }
      }
      setRunning(false);
    } catch (e) {
      setRunning(false);
      setStatus(null);
      setError(e.message);
    }
  };

  const isDone = TERMINAL.includes(status);

  if (loadError) return (
    <div className="app-shell">
      <nav className="navbar">
        <a href="/" className="navbar-brand">Orbit <span className="navbar-badge">BETA</span></a>
      </nav>
      <div className="page">
        <div className="card">
          <div className="alert alert-error">This link is invalid or has been removed.</div>
          <div className="btn-row" style={{marginTop:"1rem"}}>
            <a href="/"><button className="btn-secondary">← Create your own</button></a>
          </div>
        </div>
      </div>
    </div>
  );

  if (!manual) return (
    <div className="app-shell">
      <nav className="navbar">
        <a href="/" className="navbar-brand">Orbit <span className="navbar-badge">BETA</span></a>
      </nav>
      <div className="page">
        <div className="card">
          <p style={{color:"var(--muted)"}}>Loading automation…</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="app-shell">
      <nav className="navbar">
        <a href="/" className="navbar-brand">Orbit <span className="navbar-badge">BETA</span></a>
        {status && <StatusPill status={status} />}
      </nav>

      <div className="page">
        {/* Header */}
        <div style={{marginBottom:"1.5rem"}}>
          <h2 style={{fontSize:"1.6rem",fontWeight:700,letterSpacing:"-0.5px",marginBottom:"0.4rem"}}>
            {manual.title || "Run automation"}
          </h2>
          <p style={{color:"var(--muted)",fontSize:"0.95rem"}}>{manual.task}</p>
          {manual.url && (
            <p style={{color:"var(--muted)",fontSize:"0.82rem",marginTop:"4px"}}>
              Starting at: <span style={{color:"var(--accent2)"}}>{manual.url}</span>
            </p>
          )}
        </div>

        {/* Run card */}
        <div className="card">
          <div className="card-title">Browser automation</div>
          <ScreenshotViewer screenshots={screenshots} status={status} />

          {output && (
            <div className="result-box success">
              <strong style={{display:"block",marginBottom:"0.5rem",fontSize:"0.8rem",color:"var(--success)"}}>RESULT</strong>
              {output}
            </div>
          )}
          {error && (
            <div className="result-box error">
              {error === "Agent did not produce an answer"
                ? "The agent ran out of steps before finishing. Ask the creator to increase the step limit."
                : error}
            </div>
          )}

          <div className="btn-row">
            {!running && !isDone && (
              <button className="btn-primary" onClick={runAutomation}>
                ▶ Run this automation
              </button>
            )}
            {running && (
              <button className="btn-primary" disabled>Running…</button>
            )}
            {isDone && (
              <button className="btn-secondary" onClick={runAutomation}>↺ Run again</button>
            )}
            <a href="/"><button className="btn-ghost">Create your own →</button></a>
          </div>
        </div>

        {/* Info footer */}
        <p style={{color:"var(--muted)",fontSize:"0.8rem",textAlign:"center",marginTop:"1rem"}}>
          This automation runs in an isolated browser session — your accounts and data are never shared with anyone else.
        </p>
      </div>
    </div>
  );
}
