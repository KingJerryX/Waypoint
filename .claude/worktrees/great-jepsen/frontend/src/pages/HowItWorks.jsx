import { Link } from "react-router-dom";

const steps = [
  {
    icon: "edit_note",
    number: "01",
    title: "Describe your task",
    description:
      "Type what you want done in plain English. No code, no configuration — just tell Waypoint what you need.",
    detail: "Examples: \"Find the cheapest flights to Miami next week\", \"Summarize the top Hacker News stories\", or \"Search Amazon for mechanical keyboards under $100\".",
  },
  {
    icon: "smart_toy",
    number: "02",
    title: "AI takes the wheel",
    description:
      "Waypoint spins up a real browser and uses AI to navigate, click, type, and interact — exactly like a human would.",
    detail: "Powered by Gemini and Playwright, the agent sees the page, decides the next action, and executes it — step by step until the task is complete.",
  },
  {
    icon: "monitor",
    number: "03",
    title: "Watch it live",
    description:
      "See a live screenshot stream of the browser as it works. You stay in control and can watch every step.",
    detail: "Each frame is streamed to your browser in real time. You can see exactly what the AI sees and does — full transparency.",
  },
  {
    icon: "share",
    number: "04",
    title: "Share with anyone",
    description:
      "Turn any automation into a shareable link. Anyone with the link can re-run your exact workflow — no setup needed.",
    detail: "Generate a unique URL that packages your prompt, starting URL, and settings. Recipients click the link and the automation runs immediately.",
  },
];

const faqs = [
  {
    q: "What kinds of tasks can Waypoint handle?",
    a: "Anything a human can do in a browser: searching, filling forms, extracting data, navigating multi-step flows, summarizing pages, and more. The AI is most reliable on public websites that don't require login.",
  },
  {
    q: "Does it work on sites that require login?",
    a: "Waypoint runs a visible browser window on your machine, so you can log in manually before starting an automation. For shared links, the automation runs on the recipient's end — they'd need their own accounts.",
  },
  {
    q: "How many steps does an automation take?",
    a: "Waypoint estimates the steps automatically based on your prompt. Simple tasks like \"summarize this page\" may take 3–5 steps; complex multi-site tasks can take 15–25. You can adjust the limit in Options.",
  },
  {
    q: "Is my data private?",
    a: "Automations run locally on your machine. Screenshots and results are only stored in your browser's local storage unless you choose to create a shareable link. Shared links store only your prompt and settings — not screenshots.",
  },
];

export default function HowItWorks() {
  return (
    <div className="min-h-screen bg-[#0a1118] text-slate-100 flex flex-col">

      {/* Background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: -1 }}>
        <div className="absolute" style={{ top: "-5%", right: "-5%", width: 500, height: 500, background: "rgba(0,212,255,0.06)", borderRadius: "50%", filter: "blur(120px)" }} />
        <div className="absolute" style={{ bottom: "10%", left: "-5%", width: 400, height: 400, background: "rgba(30,64,175,0.06)", borderRadius: "50%", filter: "blur(100px)" }} />
      </div>

      {/* Header */}
      <header className="flex items-center justify-between px-6 md:px-12 py-6">
        <Link to="/" className="flex items-center gap-2 no-underline" style={{ textDecoration: "none" }}>
          <span className="material-symbols-outlined" style={{ color: "#00d4ff", fontSize: 32 }}>deployed_code</span>
          <h2 className="text-white font-bold tracking-tight text-2xl" style={{ margin: 0 }}>Waypoint</h2>
          <span className="text-[10px] font-bold rounded-full px-2 py-0.5 uppercase tracking-widest ml-1" style={{ background: "rgba(0,212,255,0.1)", color: "#00d4ff", border: "1px solid rgba(0,212,255,0.2)" }}>Beta</span>
        </Link>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm transition-colors"
          style={{ color: "#94a3b8", textDecoration: "none" }}
          onMouseEnter={e => e.currentTarget.style.color = "#fff"}
          onMouseLeave={e => e.currentTarget.style.color = "#94a3b8"}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
          Back to Waypoint
        </Link>
      </header>

      <main className="flex-1 px-6 pb-24">
        <div className="mx-auto" style={{ maxWidth: 800 }}>

          {/* Hero */}
          <div className="text-center mb-20 mt-8">
            <span className="inline-block px-3 py-1 text-xs font-bold tracking-widest uppercase rounded-full mb-5" style={{ color: "#00d4ff", background: "rgba(0,212,255,0.1)", border: "1px solid rgba(0,212,255,0.2)" }}>
              How it works
            </span>
            <h1 className="text-white font-bold leading-tight mb-5" style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(2rem, 5vw, 3rem)" }}>
              Browser automation,<br /><em style={{ color: "#00d4ff" }}>as simple as a sentence</em>
            </h1>
            <p className="text-slate-400 text-lg mx-auto leading-relaxed" style={{ maxWidth: 540 }}>
              Waypoint combines a real browser with AI to execute any web task you can describe — and lets you share those automations with the world.
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-6 mb-20">
            {steps.map((step, i) => (
              <div
                key={i}
                className="rounded-2xl p-8 flex gap-7 items-start"
                style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.08)", boxShadow: "0 2px 24px rgba(0,0,0,0.3)" }}
              >
                <div
                  className="flex-shrink-0 flex items-center justify-center rounded-2xl"
                  style={{ width: 64, height: 64, background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.15)" }}
                >
                  <span className="material-symbols-outlined" style={{ color: "#00d4ff", fontSize: 30 }}>{step.icon}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-black tracking-widest" style={{ color: "rgba(0,212,255,0.4)" }}>{step.number}</span>
                    <h2 className="text-white font-bold text-xl" style={{ margin: 0 }}>{step.title}</h2>
                  </div>
                  <p className="text-slate-300 mb-3 leading-relaxed">{step.description}</p>
                  <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>{step.detail}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Tech stack */}
          <div
            className="rounded-2xl p-8 mb-20 text-center"
            style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.1)", boxShadow: "0 0 40px rgba(0,212,255,0.04)" }}
          >
            <h2 className="text-white font-bold text-2xl mb-3" style={{ fontFamily: "'Playfair Display', serif" }}>
              Built on real infrastructure
            </h2>
            <p className="text-slate-400 mb-8 mx-auto leading-relaxed" style={{ maxWidth: 520 }}>
              No headless tricks. Waypoint uses a full Chromium browser, the same one you use every day — controlled by AI.
            </p>
            <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
              {[
                { label: "Playwright", desc: "Real browser control" },
                { label: "Google Gemini", desc: "AI decision making" },
                { label: "Chromium", desc: "Full browser engine" },
                { label: "SSE streaming", desc: "Live screenshot feed" },
              ].map((t, i) => (
                <div key={i} className="rounded-xl py-5 px-4" style={{ background: "#0a1118", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <p className="font-bold text-white mb-1">{t.label}</p>
                  <p className="text-xs" style={{ color: "#64748b" }}>{t.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* FAQ */}
          <div className="mb-20">
            <h2 className="text-white font-bold text-2xl text-center mb-8" style={{ fontFamily: "'Playfair Display', serif" }}>
              Frequently asked questions
            </h2>
            <div className="space-y-4">
              {faqs.map((faq, i) => (
                <div key={i} className="rounded-2xl p-6" style={{ background: "#16222c", border: "1px solid rgba(0,212,255,0.06)" }}>
                  <p className="font-semibold text-white mb-2">{faq.q}</p>
                  <p className="text-sm leading-relaxed" style={{ color: "#94a3b8" }}>{faq.a}</p>
                </div>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="text-center">
            <p className="text-slate-400 mb-6">Ready to automate something?</p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-full font-bold text-sm transition-all"
              style={{ background: "rgba(0,212,255,0.12)", color: "#00d4ff", border: "1px solid rgba(0,212,255,0.25)", boxShadow: "0 0 24px rgba(0,212,255,0.12)", textDecoration: "none" }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(0,212,255,0.2)"; e.currentTarget.style.boxShadow = "0 0 32px rgba(0,212,255,0.2)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(0,212,255,0.12)"; e.currentTarget.style.boxShadow = "0 0 24px rgba(0,212,255,0.12)"; }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>rocket_launch</span>
              Try Waypoint now
            </Link>
          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="px-12 py-8 text-center">
        <div className="flex flex-wrap items-center justify-center gap-8">
          <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Privacy Policy</a>
          <a href="#" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Terms of Service</a>
          <Link to="/" className="text-xs text-slate-600 hover:text-slate-400 transition-colors" style={{ textDecoration: "none" }}>Home</Link>
        </div>
      </footer>
    </div>
  );
}
