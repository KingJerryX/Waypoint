import { useState, useCallback } from "react";

const STORAGE_KEY = "orbit_agents";

function getAgents() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function setAgents(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

export default function Home() {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [task, setTask] = useState("");
  const [noClick, setNoClick] = useState(false);
  const [maxSteps, setMaxSteps] = useState(8);
  const [autoRun, setAutoRun] = useState(false);
  const [msg, setMsg] = useState({ text: "", error: false });
  const [shareLink, setShareLink] = useState("");
  const [agents, setAgentsState] = useState(getAgents);

  const renderAgents = useCallback(() => {
    setAgentsState(getAgents());
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setMsg({ text: "", error: false });
    setShareLink("");
    const t = title.trim();
    const u = url.trim();
    const tk = task.trim();
    if (!t || !u || !tk) {
      setMsg({ text: "Fill title, URL, and task.", error: true });
      return;
    }
    try {
      const res = await fetch("/api/manuals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: t,
          url: u,
          task: tk,
          max_steps: maxSteps,
          no_click: noClick,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const base = `${window.location.origin}/go/${data.id}`;
      setShareLink(autoRun ? `${base}?auto=1` : base);
      setMsg({
        text: autoRun ? "Manual created. Share the link — when someone opens it, the agent runs automatically." : "Manual created. Share the link — when someone opens it, they can run the agent.",
        error: false,
      });
    } catch (err) {
      setMsg({ text: err.message || "Failed to create manual", error: true });
    }
  };

  const handleSaveAsAgent = () => {
    const t = title.trim();
    const u = url.trim();
    const tk = task.trim();
    if (!t || !u || !tk) {
      setMsg({ text: "Fill title, URL, and task first.", error: true });
      return;
    }
    const list = getAgents();
    list.push({ title: t, url: u, task: tk, no_click: noClick, max_steps: maxSteps });
    setAgents(list);
    renderAgents();
    setMsg({ text: "Saved to My Agents. Use it anytime with “Use”.", error: false });
  };

  const copyLink = () => {
    if (!shareLink) return;
    navigator.clipboard.writeText(shareLink).then(
      () => setMsg({ text: "Link copied to clipboard.", error: false }),
      () => setMsg({ text: "Copy failed.", error: true })
    );
  };

  const useAgent = (index) => {
    const list = getAgents();
    const agent = list[index];
    if (!agent) return;
    setTitle(agent.title || "");
    setUrl(agent.url || "");
    setTask(agent.task || "");
    setNoClick(!!agent.no_click);
    setMaxSteps(agent.max_steps || 8);
  };

  const deleteAgent = (index) => {
    const list = getAgents().filter((_, i) => i !== index);
    setAgents(list);
    renderAgents();
  };

  return (
    <div className="wrap">
      <h1>Orbit</h1>
      <p className="sub">
        Write manuals, generate shareable links. Recipients click the link and the browser agent runs.
      </p>

      <section className="section">
        <h2>Create a manual (shareable link)</h2>
        <form onSubmit={handleCreate}>
          <label>Title (for you and the link page)</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Job posting extractor"
            required
          />
          <label>URL to open</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/job"
            required
          />
          <label>Task for the agent</label>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="e.g. Summarize qualifications and responsibilities"
            required
          />
          <div className="checkbox-row">
            <input
              type="checkbox"
              id="no-click"
              checked={noClick}
              onChange={(e) => setNoClick(e.target.checked)}
            />
            <label htmlFor="no-click" style={{ margin: 0 }}>
              Read-only (no click/type)
            </label>
          </div>
          <div className="checkbox-row">
            <input
              type="checkbox"
              id="auto-run"
              checked={autoRun}
              onChange={(e) => setAutoRun(e.target.checked)}
            />
            <label htmlFor="auto-run" style={{ margin: 0 }}>
              Auto-run when link is opened (agent runs as soon as someone opens the share link)
            </label>
          </div>
          <label>Max steps (optional)</label>
          <input
            type="number"
            value={maxSteps}
            onChange={(e) => setMaxSteps(Number(e.target.value) || 8)}
            min={1}
            max={20}
          />
          <div className="row">
            <button type="submit" className="primary">
              Create & get link
            </button>
            <button type="button" className="secondary" onClick={handleSaveAsAgent}>
              Save as My Agent
            </button>
          </div>
        </form>
        {msg.text && (
          <div className={`msg ${msg.error ? "error" : "success"}`}>{msg.text}</div>
        )}
        {shareLink && (
          <div className="link-box">
            <input type="text" value={shareLink} readOnly />
            <button type="button" className="secondary small" onClick={copyLink}>
              Copy
            </button>
          </div>
        )}
      </section>

      <section className="section">
        <h2>My agents (saved in this browser)</h2>
        <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: "0 0 1rem 0" }}>
          Reuse these when creating manuals or run locally.
        </p>
        {agents.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", margin: 0 }}>
            No saved agents yet. Create a manual and click “Save as My Agent”.
          </p>
        ) : (
          <ul className="agents-list">
            {agents.map((agent, i) => (
              <li key={i}>
                <div className="info">
                  <strong>{agent.title || "Untitled"}</strong>
                  <span>
                    {agent.url} · {(agent.task || "").slice(0, 50)}
                    {(agent.task || "").length > 50 ? "…" : ""}
                  </span>
                </div>
                <div className="actions">
                  <button type="button" className="secondary small" onClick={() => useAgent(i)}>
                    Use
                  </button>
                  <button type="button" className="secondary small" onClick={() => deleteAgent(i)}>
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
