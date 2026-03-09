import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";

const STORAGE_KEY = "orbit_saved_v2";
function getSaved() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}
function setSaved(list) { localStorage.setItem(STORAGE_KEY, JSON.stringify(list)); }

const TERMINAL = ["completed", "failed", "terminated", "timed_out", "canceled"];

const SUGGESTIONS = [
  "Go to Hacker News and summarize the top 5 stories",
  "Find the cheapest one-way flights to Miami next week",
  "Search Amazon for the best mechanical keyboard under $100",
];

function StatusPill({ status }) {
  const active = status === "running" || status === "queued" || status === "created";
  const colors = {
    running: "bg-yellow-400/15 text-yellow-400",
    paused: "bg-amber-400/15 text-amber-400",
    completed: "bg-emerald-400/15 text-emerald-400",
    failed: "bg-red-400/15 text-red-400",
    queued: "bg-cyan-400/15 text-cyan-400",
    created: "bg-cyan-400/15 text-cyan-400",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${colors[status] || "bg-slate-700 text-slate-400"}`}>
      {active && <span className="w-2 h-2 rounded-full bg-current animate-pulse" />}
      {status}
    </span>
  );
}

function ScreenshotViewer({ screenshot, stepCount, status }) {
  return (
    <div className="relative w-full bg-black rounded-xl overflow-hidden border border-cyan-500/10" style={{ aspectRatio: "16/10" }}>
      {screenshot ? (
        <>
          <img src={screenshot} alt="Browser screenshot" className="w-full h-full object-contain" />
          {stepCount > 1 && (
            <span className="absolute bottom-2 right-3 text-xs text-slate-400 bg-black/60 px-2 py-0.5 rounded-full">
              step {stepCount}
            </span>
          )}
        </>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-600">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2" />
            <path d="M8 21h8M12 17v4" />
          </svg>
          <span className="text-sm">{status === "running" ? "Starting browser…" : "Waiting for browser…"}</span>
        </div>
      )}
    </div>
  );
}

function ActivityLog({ log, scrollRef }) {
  if (!log.length) return null;
  return (
    <div className="w-full rounded-xl overflow-hidden" style={{ background: "#0d1622", border: "1px solid rgba(0,212,255,0.1)" }}>
      <div className="px-4 py-2 flex items-center gap-2 border-b" style={{ borderColor: "rgba(0,212,255,0.08)" }}>
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "#475569" }}>Activity</span>
      </div>
      <div
        ref={scrollRef}
        className="px-4 py-2 space-y-1 overflow-y-auto"
        style={{ maxHeight: 140 }}
      >
        {log.map((item, i) => {
          const isLatest = i === log.length - 1;
          return (
            <div key={i} className="flex items-center gap-3 text-xs">
              <span className="font-mono shrink-0" style={{ color: "#334155", minWidth: 28 }}>
                #{item.step}
              </span>
              <span style={{ color: isLatest ? "#00d4ff" : "#475569" }}>
                {item.message}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [url, setUrl] = useState("");
  const [maxSteps, setMaxSteps] = useState(15);
  const [estimating, setEstimating] = useState(false);
  const estimateTimer = useRef(null);

  const [status, setStatus] = useState(null);
  const [latestScreenshot, setLatestScreenshot] = useState(null);
  const [stepCount, setStepCount] = useState(0);
  const [activityLog, setActivityLog] = useState([]);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const activityEndRef = useRef(null);

  const [shareTitle, setShareTitle] = useState("");
  const [shareLink, setShareLink] = useState("");
  const [shareMsg, setShareMsg] = useState(null);
  const [copied, setCopied] = useState(false);

  const [paused, setPaused] = useState(null); // { session_id, reason } when agent is waiting

  const [saved, setSavedState] = useState(getSaved);
  const [showSaved, setShowSaved] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Auto-scroll activity log to bottom on new entries
  useEffect(() => {
    if (activityEndRef.current) {
      activityEndRef.current.scrollTop = activityEndRef.current.scrollHeight;
    }
  }, [activityLog]);

  useEffect(() => {
    if (estimateTimer.current) clearTimeout(estimateTimer.current);
    if (!prompt.trim() || prompt.trim().length < 15) return;
    estimateTimer.current = setTimeout(async () => {
      setEstimating(true);
      try {
        const r = await fetch("/api/estimate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: prompt.trim() }),
        });
        const data = await r.json();
        if (data.steps) setMaxSteps(data.steps);
      } catch {}
      setEstimating(false);
    }, 800);
    return () => clearTimeout(estimateTimer.current);
  }, [prompt]);

  const handleRun = async () => {
    if (!prompt.trim() || running) return;
    setRunning(true);
    setStatus("running");
    setLatestScreenshot(null);
    setStepCount(0);
    setActivityLog([]);
    setOutput(null);
    setError(null);
    setShareLink("");
    setShareMsg(null);

    try {
      const response = await fetch("/api/run/local", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim(), url: url.trim() || undefined, max_steps: maxSteps }),
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
            if (event.type === "status") setStatus(event.status);
            else if (event.type === "screenshot") {
              setStatus("running");
              // Replace instead of append — only the latest frame matters, prevents memory growth
              setLatestScreenshot(`data:image/png;base64,${event.data}`);
              setStepCount(n => n + 1);
            } else if (event.type === "activity") {
              setActivityLog(prev => [...prev, { step: event.step, message: event.message }]);
            } else if (event.type === "human_required") {
              setStatus("paused");
              setPaused({ session_id: event.session_id, reason: event.reason });
            } else if (event.type === "done") {
              setStatus(event.ok ? "completed" : "failed");
              setRunning(false);
              setPaused(null);
              if (event.ok) setOutput(event.answer || "Task completed successfully.");
              else setError(event.error || "Task failed.");
            } else if (event.type === "error") {
              setRunning(false);
              setStatus("failed");
              setPaused(null);
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

  const handleShare = async () => {
    const t = shareTitle.trim() || prompt.slice(0, 60);
    if (!prompt.trim()) { setShareMsg({ text: "Enter a prompt first.", error: true }); return; }
    try {
      const r = await fetch("/api/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: t, prompt: prompt.trim(), url: url.trim() || undefined, max_steps: maxSteps }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail);
      const link = `${window.location.origin}/go/${data.id}`;
      setShareLink(link);
      setShareMsg({ text: "Link created! Anyone with this link can run your automation.", error: false });
    } catch (e) {
      setShareMsg({ text: e.message || "Failed to create link", error: true });
    }
  };

  const copyLink = () => {
    navigator.clipboard.writeText(shareLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleResume = async () => {
    if (!paused?.session_id) return;
    try {
      await fetch(`/api/resume/${paused.session_id}`, { method: "POST" });
      setPaused(null);
      setStatus("running");
    } catch (e) {
      console.error("Resume failed:", e);
    }
  };

  const saveToLibrary = () => {
    if (!prompt.trim()) return;
    const t = shareTitle.trim() || prompt.slice(0, 60);
    const list = getSaved();
    list.unshift({ title: t, prompt: prompt.trim(), url: url.trim(), max_steps: maxSteps, ts: Date.now() });
    setSaved(list.slice(0, 20));
    setSavedState(list.slice(0, 20));
  };

  const loadSaved = (item) => {
    setPrompt(item.prompt);
    setUrl(item.url || "");
    setMaxSteps(item.max_steps || 15);
    setShareTitle(item.title || "");
    setShowSaved(false);
  };

  const deleteSaved = (i) => {
    const list = getSaved().filter((_, idx) => idx !== i);
    setSaved(list);
    setSavedState(list);
  };

  const isDone = TERMINAL.includes(status);
  const isIdle = !status && !running;

  return (
    <div className="min-h-screen bg-[#0a1118] text-slate-100 flex flex-col relative overflow-x-hidden">

      {/* Background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: -1 }}>
        <div className="absolute" style={{ top: "-10%", right: "-10%", width: 500, height: 500, background: "rgba(0,212,255,0.08)", borderRadius: "50%", filter: "blur(120px)" }} />
        <div className="absolute" style={{ bottom: "-10%", left: "-10%", width: 400, height: 400, background: "rgba(30,64,175,0.08)", borderRadius: "50%", filter: "blur(100px)" }} />
      </div>

      {/* Header */}
      <header className="flex items-center justify-between px-6 md:px-12 py-6">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined" style={{ color: "#00d4ff", fontSize: 32 }}>deployed_code</span>
          <h2 className="text-white font-bold tracking-tight text-2xl">Waypoint</h2>
          <span className="text-[10px] font-bold rounded-full px-2 py-0.5 uppercase tracking-widest ml-1" style={{ background: "rgba(0,212,255,0.1)", color: "#00d4ff", border: "1px solid rgba(0,212,255,0.2)" }}>Beta</span>
        </div>
        <div className="flex items-center gap-4">
          {status && <StatusPill status={status} />}
          {saved.length > 0 && (
            <button onClick={() => setShowSaved(s => !s)} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors">
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>history</span>
              Saved
            </button>
          )}
          <Link
            to="/how-it-works"
            className="flex items-center gap-1.5 text-sm transition-colors"
            style={{ color: "#94a3b8", textDecoration: "none" }}
            onMouseEnter={e => e.currentTarget.style.color = "#fff"}
            onMouseLeave={e => e.currentTarget.style.color = "#94a3b8"}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>help_outline</span>
            How it works
          </Link>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center px-6 pb-16 text-center">
        <div className="w-full space-y-8 mt-6" style={{ maxWidth: 800 }}>

          {/* Hero */}
          {isIdle && (
            <div className="space-y-5">
              <span className="inline-block px-3 py-1 text-xs font-bold tracking-widest uppercase rounded-full" style={{ color: "#00d4ff", background: "rgba(0,212,255,0.1)", border: "1px solid rgba(0,212,255,0.2)" }}>
                Workflow Intelligence
              </span>
              <h1 className="text-white font-bold leading-tight" style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(2.5rem, 6vw, 3.75rem)" }}>
                What will you <em style={{ color: "#00d4ff" }}>automate</em> today?
              </h1>
              <p className="text-slate-400 text-lg mx-auto leading-relaxed" style={{ maxWidth: 520 }}>
                Describe a task. Watch AI take control of the browser and do it for you — then share it with anyone.
              </p>
            </div>
          )}

          {/* Prompt input */}
          <div className="flex flex-col items-center w-full mx-auto" style={{ maxWidth: 672 }}>
            <div className="relative w-full">
              <div className="absolute rounded-2xl" style={{ inset: -4, background: "linear-gradient(135deg, rgba(0,212,255,0.3), rgba(37,99,235,0.3))", filter: "blur(8px)", opacity: 0.2 }} />
              <div className="relative flex items-stretch rounded-2xl" style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.2)", boxShadow: "0 0 24px rgba(0,212,255,0.12)" }}>
                <textarea
                  className="flex-1 resize-none bg-transparent text-white pl-6 pr-2 py-5 text-lg outline-none rounded-l-2xl leading-relaxed"
                  style={{ color: "white", caretColor: "#00d4ff" }}
                  placeholder="Enter a prompt to build your workflow..."
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  rows={2}
                  onKeyDown={e => {
                    if (e.key === "Enter" && !e.shiftKey && !running) { e.preventDefault(); handleRun(); }
                  }}
                />
                <button
                  onClick={handleRun}
                  disabled={running || !prompt.trim()}
                  className="flex items-center justify-center px-6 rounded-r-2xl transition-all"
                  style={{
                    color: "#00d4ff",
                    borderLeft: "1px solid rgba(0,212,255,0.1)",
                    cursor: running || !prompt.trim() ? "not-allowed" : "pointer",
                    opacity: running || !prompt.trim() ? 0.35 : 1,
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 24 }}>
                    {running ? "hourglass_empty" : "send"}
                  </span>
                </button>
              </div>
            </div>

            {/* Options toggle */}
            <button
              onClick={() => setShowAdvanced(s => !s)}
              className="mt-3 flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{showAdvanced ? "expand_less" : "tune"}</span>
              {showAdvanced ? "Hide options" : "Options"}
            </button>

            {showAdvanced && (
              <div className="mt-3 w-full flex flex-wrap gap-3 items-center justify-center text-sm">
                <input
                  type="url"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="Starting URL (optional)"
                  className="rounded-xl px-4 py-2 text-sm outline-none"
                  style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.12)", color: "#cbd5e1", width: 220 }}
                />
                <div className="flex items-center gap-2 text-slate-500">
                  <span>Max steps:</span>
                  <strong className="text-slate-300">{maxSteps}</strong>
                  {estimating && <span className="text-xs text-slate-600">estimating…</span>}
                  <input
                    type="range" min={5} max={25} value={maxSteps}
                    onChange={e => setMaxSteps(Number(e.target.value))}
                    style={{ width: 96, accentColor: "#00d4ff" }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Suggestion chips */}
          {isIdle && (
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setPrompt(s)}
                  className="px-4 py-2 rounded-full text-xs transition-all"
                  style={{ background: "rgba(0,212,255,0.04)", color: "rgba(0,212,255,0.6)", border: "1px solid rgba(0,212,255,0.1)" }}
                  onMouseEnter={e => { e.currentTarget.style.background = "rgba(0,212,255,0.1)"; e.currentTarget.style.color = "#00d4ff"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "rgba(0,212,255,0.04)"; e.currentTarget.style.color = "rgba(0,212,255,0.6)"; }}
                >
                  "{s}"
                </button>
              ))}
            </div>
          )}

          {/* Human takeover banner */}
          {paused && (
            <div className="w-full mx-auto text-left" style={{ maxWidth: 672 }}>
              <div className="rounded-2xl p-5 flex items-start gap-4" style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.3)", boxShadow: "0 0 24px rgba(251,191,36,0.08)" }}>
                <span className="material-symbols-outlined flex-shrink-0 mt-0.5" style={{ color: "#fbbf24", fontSize: 24 }}>person_raised_hand</span>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-white mb-1">Your turn</p>
                  <p className="text-sm mb-3" style={{ color: "#fbbf24" }}>{paused.reason}</p>
                  <p className="text-xs mb-4" style={{ color: "#94a3b8" }}>
                    Complete the action in the browser window that opened on your screen, then click <strong className="text-white">Continue</strong> to let the agent take back over.
                  </p>
                  <button
                    onClick={handleResume}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold transition-all"
                    style={{ background: "rgba(251,191,36,0.15)", color: "#fbbf24", border: "1px solid rgba(251,191,36,0.3)" }}
                    onMouseEnter={e => { e.currentTarget.style.background = "rgba(251,191,36,0.25)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "rgba(251,191,36,0.15)"; }}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>play_arrow</span>
                    Continue — I'm done
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Live browser */}
          {(status || running) && (
            <div className="w-full mx-auto space-y-4 text-left" style={{ maxWidth: 672 }}>
              <ScreenshotViewer screenshot={latestScreenshot} stepCount={stepCount} status={status} />
              <ActivityLog log={activityLog} scrollRef={activityEndRef} />

              {output && (
                <div className="rounded-xl p-5 text-sm leading-relaxed whitespace-pre-wrap" style={{ background: "#16222c", border: "1px solid rgba(52,211,153,0.2)" }}>
                  <strong className="block text-xs uppercase tracking-wider mb-2" style={{ color: "#34d399" }}>Result</strong>
                  {output}
                </div>
              )}
              {error && (
                <div className="rounded-xl p-4 text-sm" style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", color: "#f87171" }}>
                  {error === "Agent did not produce an answer"
                    ? "The agent ran out of steps before finishing. Increase Max steps and try again."
                    : error}
                </div>
              )}

              {isDone && (
                <button
                  onClick={() => { setStatus(null); setScreenshots([]); setOutput(null); setError(null); }}
                  className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>restart_alt</span>
                  Run again
                </button>
              )}
            </div>
          )}

          {/* Share section */}
          {isDone && (
            <div className="w-full mx-auto text-left" style={{ maxWidth: 672 }}>
              <div className="rounded-2xl p-5 space-y-3" style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.12)", boxShadow: "0 0 24px rgba(0,212,255,0.08)" }}>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Share this automation</p>
                <input
                  type="text"
                  value={shareTitle}
                  onChange={e => setShareTitle(e.target.value)}
                  placeholder={prompt.slice(0, 60) || "My automation"}
                  className="w-full rounded-xl px-4 py-2 text-sm outline-none"
                  style={{ background: "#0a1118", border: "1px solid rgba(0,212,255,0.1)", color: "#cbd5e1" }}
                />
                <div className="flex gap-2 flex-wrap">
                  <button onClick={handleShare} className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm transition-all" style={{ background: "rgba(0,212,255,0.1)", color: "#00d4ff", border: "1px solid rgba(0,212,255,0.2)" }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>link</span>
                    Generate link
                  </button>
                  <button onClick={saveToLibrary} className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm transition-all" style={{ background: "rgba(255,255,255,0.04)", color: "#94a3b8", border: "1px solid rgba(255,255,255,0.08)" }}>
                    + Save to library
                  </button>
                </div>
                {shareMsg && (
                  <p className="text-xs" style={{ color: shareMsg.error ? "#f87171" : "#34d399" }}>{shareMsg.text}</p>
                )}
                {shareLink && (
                  <div className="flex items-center gap-2 rounded-xl px-4 py-2" style={{ background: "#0a1118", border: "1px solid rgba(0,212,255,0.1)" }}>
                    <input type="text" value={shareLink} readOnly className="flex-1 bg-transparent text-sm font-mono outline-none" style={{ color: "#00d4ff" }} />
                    <button onClick={copyLink} className="text-xs flex-shrink-0 transition-colors" style={{ color: copied ? "#34d399" : "#64748b" }}>
                      {copied ? "✓ Copied" : "Copy"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Saved library */}
          {showSaved && saved.length > 0 && (
            <div className="w-full mx-auto text-left" style={{ maxWidth: 672 }}>
              <div className="rounded-2xl p-5 space-y-2" style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.1)" }}>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">Saved automations</p>
                {saved.map((item, i) => (
                  <div key={i} className="flex items-center justify-between rounded-xl px-4 py-3 gap-3" style={{ background: "#0a1118", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-sm font-medium text-slate-200 truncate">{item.title || "Untitled"}</p>
                      <p className="text-xs text-slate-500 truncate">{(item.prompt || "").slice(0, 70)}</p>
                    </div>
                    <div className="flex gap-3 flex-shrink-0">
                      <button onClick={() => loadSaved(item)} className="text-xs" style={{ color: "#00d4ff" }}>Load</button>
                      <button onClick={() => deleteSaved(i)} className="text-xs" style={{ color: "#f87171" }}>✕</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="px-12 py-8 text-center">
        <div className="flex flex-wrap items-center justify-center gap-8">
          <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Privacy Policy</a>
          <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Terms of Service</a>
          <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Documentation</a>
        </div>
      </footer>
    </div>
  );
}
