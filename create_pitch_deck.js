/**
 * Waypoint Pitch Deck — pptxgenjs
 * Slide deck: 12 slides, dark navy theme, cyan accent
 * Run: node create_pitch_deck.js
 */
const pptxgen = require("pptxgenjs");

// ─── THEME ────────────────────────────────────────────────────────────────────
const C = {
  bg:        "0A1628",
  bgCard:    "112038",
  bgDeep:    "060F1E",
  bgMid:     "0D1F35",
  cyan:      "00C8FF",
  purple:    "7B61FF",
  green:     "00D4A0",
  orange:    "FF9500",
  white:     "FFFFFF",
  muted:     "7A9BBE",
  dim:       "2A4060",
  red:       "FF5A5A",
};

const FONT = "Calibri";

let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10" x 5.625"
pres.title  = "Waypoint — Investor Pitch Deck";
pres.author = "Waypoint";

const W = 10, H = 5.625;

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function mkSlide(bg = C.bg) {
  const s = pres.addSlide();
  s.background = { color: bg };
  return s;
}

function label(s, text) {
  s.addText(text.toUpperCase(), {
    x: 0.5, y: 0.2, w: 5, h: 0.25,
    fontSize: 9, fontFace: FONT, color: C.cyan,
    bold: true, charSpacing: 3, margin: 0,
  });
}

function title(s, text, y = 0.52) {
  s.addText(text, {
    x: 0.5, y, w: 9, h: 0.65,
    fontSize: 30, fontFace: FONT, color: C.white,
    bold: true, margin: 0,
  });
}

function divider(s, y = 1.6) {
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 9, h: 0.015,
    fill: { color: C.dim }, line: { color: C.dim, width: 0 },
  });
}

function sub(s, text, y = 1.25) {
  s.addText(text, {
    x: 0.5, y, w: 9, h: 0.32,
    fontSize: 13, fontFace: FONT, color: C.muted, margin: 0,
  });
}

// Card with left accent bar (RECTANGLE only, no rounded)
function card(s, x, y, w, h, { fill = C.bgCard, accent = C.cyan, border = C.dim } = {}) {
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: fill },
    line: { color: border, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.04, h,
    fill: { color: accent }, line: { color: accent, width: 0 },
  });
}

// ─── SLIDE 1: COVER ───────────────────────────────────────────────────────────
{
  const s = mkSlide(C.bgDeep);

  // Left dark panel
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 4.4, h: H,
    fill: { color: "040A14" }, line: { color: "040A14", width: 0 },
  });
  // Vertical cyan divider line
  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.4, y: 0, w: 0.04, h: H,
    fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
  });

  // Glow circle — top right
  s.addShape(pres.shapes.OVAL, {
    x: 7.2, y: -1.8, w: 4.5, h: 4.5,
    fill: { color: "00C8FF", transparency: 88 }, line: { color: "00C8FF", width: 0 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 7.9, y: -1.1, w: 3.2, h: 3.2,
    fill: { color: "00C8FF", transparency: 93 }, line: { color: "00C8FF", width: 0 },
  });

  // Right panel content
  s.addText("INVESTOR PITCH   2025", {
    x: 4.6, y: 1.0, w: 5.2, h: 0.3,
    fontSize: 9, fontFace: FONT, color: C.cyan,
    bold: true, charSpacing: 3, margin: 0,
  });
  s.addText("WAYPOINT", {
    x: 4.6, y: 1.38, w: 5.2, h: 1.05,
    fontSize: 62, fontFace: FONT, color: C.white,
    bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("Automate anything.", {
    x: 4.6, y: 2.58, w: 5.2, h: 0.42,
    fontSize: 20, fontFace: FONT, color: C.muted, margin: 0,
  });
  s.addText("Share the result.", {
    x: 4.6, y: 3.0, w: 5.2, h: 0.42,
    fontSize: 20, fontFace: FONT, color: C.cyan, bold: true, margin: 0,
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.6, y: 4.45, w: 5.0, h: 0.015,
    fill: { color: C.dim }, line: { color: C.dim, width: 0 },
  });
  s.addText("AI Browser Automation Platform  |  waypoint.app", {
    x: 4.6, y: 4.55, w: 5.0, h: 0.3,
    fontSize: 10.5, fontFace: FONT, color: C.muted, margin: 0,
  });

  // Left panel — logo mark: concentric circles (map pin / waypoint icon)
  s.addShape(pres.shapes.OVAL, {
    x: 1.3, y: 1.45, w: 1.8, h: 1.8,
    fill: { color: C.cyan, transparency: 0 }, line: { color: C.cyan, width: 0 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 1.45, y: 1.6, w: 1.5, h: 1.5,
    fill: { color: "040A14" }, line: { color: "040A14", width: 0 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 1.72, y: 1.87, w: 0.96, h: 0.96,
    fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
  });
  s.addText("AI Browser Automation", {
    x: 0.2, y: 3.55, w: 4.0, h: 0.35,
    fontSize: 11, fontFace: FONT, color: C.muted,
    align: "center", margin: 0,
  });
}

// ─── SLIDE 2: PROBLEM ─────────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "The Problem");
  title(s, "Web Intelligence Is Trapped");
  sub(s, "Knowledge workers spend hours every day on tasks that should take seconds.");
  divider(s);

  const problems = [
    {
      n: "01", color: C.cyan,
      heading: "Web tasks are\nmanual & repetitive",
      body: "Searching flights, scraping prices, filling forms, monitoring pages — everyone does them, nobody likes them.",
    },
    {
      n: "02", color: C.purple,
      heading: "Automation requires\na developer",
      body: "Selenium, Playwright, Zapier all need technical setup. They break when sites change. Non-technical users are locked out.",
    },
    {
      n: "03", color: C.orange,
      heading: "AI assistants talk\nbut don't act",
      body: "ChatGPT tells you what flight to book — but you still have to book it yourself. Results die on your screen.",
    },
  ];

  const cW = 2.9, cH = 2.88, cY = 1.75, gap = 0.17;
  problems.forEach((p, i) => {
    const x = 0.5 + i * (cW + gap);
    card(s, x, cY, cW, cH, { accent: p.color });

    s.addText(p.n, {
      x: x + 0.18, y: cY + 0.2, w: 0.72, h: 0.55,
      fontSize: 30, fontFace: FONT, color: p.color, bold: true, margin: 0,
    });
    s.addText(p.heading, {
      x: x + 0.18, y: cY + 0.85, w: cW - 0.28, h: 0.82,
      fontSize: 14, fontFace: FONT, color: C.white, bold: true, margin: 0,
    });
    s.addText(p.body, {
      x: x + 0.18, y: cY + 1.74, w: cW - 0.28, h: 1.0,
      fontSize: 11.5, fontFace: FONT, color: C.muted, margin: 0,
    });
  });
}

// ─── SLIDE 3: SOLUTION ────────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "The Solution");

  s.addText("Introducing", {
    x: 0.5, y: 0.65, w: 9, h: 0.38,
    fontSize: 16, fontFace: FONT, color: C.muted, align: "center", margin: 0,
  });
  s.addText("WAYPOINT", {
    x: 0.5, y: 1.08, w: 9, h: 0.9,
    fontSize: 56, fontFace: FONT, color: C.white,
    bold: true, charSpacing: 4, align: "center", margin: 0,
  });

  // Cyan accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 4.0, y: 2.06, w: 2.0, h: 0.055,
    fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
  });

  s.addText("An AI browser agent that executes any web task in natural language —", {
    x: 0.5, y: 2.22, w: 9, h: 0.44,
    fontSize: 17, fontFace: FONT, color: C.white, align: "center", margin: 0,
  });
  s.addText("and makes the result a permanent, shareable link anyone can see.", {
    x: 0.5, y: 2.68, w: 9, h: 0.44,
    fontSize: 17, fontFace: FONT, color: C.cyan,
    bold: true, align: "center", margin: 0,
  });

  // 3 pillars
  const pillars = [
    { label: "Any Website", detail: "Works on any site, no integrations needed" },
    { label: "Natural Language", detail: "Just describe the task in plain English" },
    { label: "Shareable Results", detail: "One link — anyone can view the output" },
  ];
  const pW = 2.65, pH = 1.1, pY = 3.35, pGap = 0.51;
  pillars.forEach((p, i) => {
    const x = 0.72 + i * (pW + pGap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: pY, w: pW, h: pH,
      fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: pY, w: pW, h: 0.055,
      fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
    });
    s.addText(p.label, {
      x: x + 0.15, y: pY + 0.15, w: pW - 0.2, h: 0.35,
      fontSize: 13, fontFace: FONT, color: C.white, bold: true, margin: 0,
    });
    s.addText(p.detail, {
      x: x + 0.15, y: pY + 0.52, w: pW - 0.2, h: 0.46,
      fontSize: 10.5, fontFace: FONT, color: C.muted, margin: 0,
    });
  });
}

// ─── SLIDE 4: PRODUCT DEMO ────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Product");
  title(s, "See It In Action");

  // Input prompt box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.32, w: 9, h: 0.6,
    fill: { color: C.bgCard }, line: { color: C.cyan, width: 1.5 },
  });
  s.addText("  Find the cheapest nonstop one-way flight from BOS to SJU next week for one person", {
    x: 0.6, y: 1.38, w: 8.7, h: 0.47,
    fontSize: 13, fontFace: FONT, color: C.white,
    italic: true, valign: "middle", margin: 0,
  });

  // Arrow
  s.addShape(pres.shapes.LINE, {
    x: 4.98, y: 1.95, w: 0.001, h: 0.22,
    line: { color: C.cyan, width: 2 },
  });

  // 4 step boxes
  const steps = [
    "Opening Google Flights",
    "Selecting One way, BOS to SJU",
    "Picking dates, filtering Nonstop",
    "Reading and ranking results",
  ];
  const sW = 2.1, sH = 0.6, sY = 2.2, sGap = 0.12;
  steps.forEach((st, i) => {
    const x = 0.5 + i * (sW + sGap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: sY, w: sW, h: sH,
      fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
    });
    // Step circle
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.08, y: sY + 0.1, w: 0.38, h: 0.38,
      fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
    });
    s.addText(String(i + 1), {
      x: x + 0.08, y: sY + 0.1, w: 0.38, h: 0.38,
      fontSize: 11, fontFace: FONT, color: C.bg,
      bold: true, align: "center", valign: "middle", margin: 0,
    });
    s.addText(st, {
      x: x + 0.54, y: sY + 0.08, w: sW - 0.62, h: 0.44,
      fontSize: 10, fontFace: FONT, color: C.white, valign: "middle", margin: 0,
    });
    // Arrow
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.LINE, {
        x: x + sW, y: sY + sH / 2, w: sGap, h: 0,
        line: { color: C.cyan, width: 1.5 },
      });
    }
  });

  // Arrow
  s.addShape(pres.shapes.LINE, {
    x: 4.98, y: 2.83, w: 0.001, h: 0.22,
    line: { color: C.cyan, width: 2 },
  });

  // Result box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.08, w: 6.5, h: 0.72,
    fill: { color: "082214" }, line: { color: C.green, width: 1.5 },
  });
  s.addText("Spirit Airlines  |  BOS to SJU  |  Fri Jan 17  |  $89  |  Nonstop  |  3h 38m", {
    x: 0.68, y: 3.18, w: 6.15, h: 0.5,
    fontSize: 12.5, fontFace: FONT, color: C.green,
    bold: true, valign: "middle", margin: 0,
  });

  // Share link card
  s.addShape(pres.shapes.RECTANGLE, {
    x: 7.15, y: 3.08, w: 2.35, h: 0.72,
    fill: { color: C.bgCard }, line: { color: C.cyan, width: 1.5 },
  });
  s.addText("Share this result", {
    x: 7.25, y: 3.15, w: 2.15, h: 0.3,
    fontSize: 11, fontFace: FONT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("waypoint.app/go/abc123", {
    x: 7.25, y: 3.48, w: 2.15, h: 0.25,
    fontSize: 9.5, fontFace: FONT, color: C.muted, margin: 0,
  });

  s.addText("No code. No setup. Anyone with the link sees the result instantly.", {
    x: 0.5, y: 3.98, w: 9, h: 0.3,
    fontSize: 12, fontFace: FONT, color: C.muted,
    italic: true, align: "center", margin: 0,
  });

  // Activity log mini panel
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.35, w: 9, h: 0.88,
    fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
  });
  s.addText("Live Activity Trace", {
    x: 0.65, y: 4.41, w: 3, h: 0.25,
    fontSize: 9, fontFace: FONT, color: C.cyan, bold: true, charSpacing: 1, margin: 0,
  });
  const logItems = ["#1 Opening Google Flights", "#2 Clicking One way", "#3 Typing BOS", "#4 Clicking airport", "#5 Typing SJU"];
  logItems.forEach((item, i) => {
    s.addText(item, {
      x: 0.65 + i * 1.82, y: 4.7, w: 1.75, h: 0.4,
      fontSize: 8.5, fontFace: FONT, color: i === 0 ? C.white : C.muted, margin: 0,
    });
  });
}

// ─── SLIDE 5: THE WAYPOINT FLYWHEEL ──────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Platform Strategy");

  // Left text column
  s.addText("The Waypoint\nFlywheel", {
    x: 0.5, y: 0.45, w: 4.5, h: 1.1,
    fontSize: 32, fontFace: FONT, color: C.white, bold: true, margin: 0,
  });
  s.addText("Every shared link is a distribution channel.\nThis is how Waypoint grows without paid acquisition.", {
    x: 0.5, y: 1.65, w: 4.3, h: 0.75,
    fontSize: 13, fontFace: FONT, color: C.muted, margin: 0,
  });

  // Quote card
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.55, w: 4.3, h: 1.25,
    fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 2.55, w: 0.04, h: 1.25,
    fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
  });
  s.addText("\"Waypoint is to browser automation what\nLoom is to screen recording — you do it\nonce, share it forever.\"", {
    x: 0.65, y: 2.65, w: 4.0, h: 1.05,
    fontSize: 12, fontFace: FONT, color: C.white, italic: true, margin: 0,
  });

  s.addText("Network effects  |  Viral growth  |  Zero paid acquisition needed", {
    x: 0.5, y: 4.0, w: 4.5, h: 0.35,
    fontSize: 11, fontFace: FONT, color: C.cyan, bold: true, margin: 0,
  });

  // Flywheel diagram — right side, center ~(7.4, 3.05)
  const cx = 7.38, cy = 3.05, r = 1.65;

  // Outer glow ring
  s.addShape(pres.shapes.OVAL, {
    x: cx - r, y: cy - r, w: r * 2, h: r * 2,
    fill: { color: "00C8FF", transparency: 91 }, line: { color: C.cyan, width: 1.5 },
  });

  // Inner hub
  s.addShape(pres.shapes.OVAL, {
    x: cx - 0.72, y: cy - 0.52, w: 1.44, h: 1.04,
    fill: { color: C.bg }, line: { color: C.cyan, width: 2 },
  });
  s.addText("WAYPOINT", {
    x: cx - 0.72, y: cy - 0.26, w: 1.44, h: 0.52,
    fontSize: 9, fontFace: FONT, color: C.cyan,
    bold: true, align: "center", charSpacing: 1, margin: 0,
  });

  // 5 flywheel nodes (evenly spaced around ring)
  const nodes = [
    { label: "User runs\nautomation",  angle: 270 },
    { label: "Gets a\nshare link",     angle: 342 },
    { label: "Shares with\nteam / web", angle: 54  },
    { label: "New users\ndiscover",    angle: 126 },
    { label: "They run\nautomations",  angle: 198 },
  ];

  nodes.forEach((nd) => {
    const rad = (nd.angle * Math.PI) / 180;
    const nx = cx + r * Math.cos(rad);
    const ny = cy + r * Math.sin(rad);

    s.addShape(pres.shapes.RECTANGLE, {
      x: nx - 0.48, y: ny - 0.33, w: 0.96, h: 0.66,
      fill: { color: C.bgCard }, line: { color: C.cyan, width: 1.5 },
    });
    s.addText(nd.label, {
      x: nx - 0.48, y: ny - 0.33, w: 0.96, h: 0.66,
      fontSize: 7.5, fontFace: FONT, color: C.white,
      align: "center", valign: "middle", margin: 0,
    });
  });
}

// ─── SLIDE 6: HOW IT WORKS ────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Product");
  title(s, "How It Works");

  const steps = [
    {
      n: "1", color: C.cyan,
      heading: "Describe Your Task",
      body: "Type what you want in plain English. No code, no configuration, no templates.",
      example: '"Find cheapest nonstop flight BOS to SJU next week"',
    },
    {
      n: "2", color: C.purple,
      heading: "Waypoint Executes It",
      body: "Our AI agent controls a real browser — clicking, typing, navigating, reading pages just like a human.",
      example: "Gemini + Playwright on a real Chromium browser",
    },
    {
      n: "3", color: C.green,
      heading: "Get the Answer & Share It",
      body: "Receive a structured result instantly. One click gives you a permanent shareable link — no login required to view.",
      example: "waypoint.app/go/abc123",
    },
  ];

  const cW = 2.9, cH = 3.35, cY = 1.4, gap = 0.17;
  steps.forEach((st, i) => {
    const x = 0.5 + i * (cW + gap);

    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: cH,
      fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
    });
    // Top color bar
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: 0.06,
      fill: { color: st.color }, line: { color: st.color, width: 0 },
    });

    s.addText(st.n, {
      x: x + 0.2, y: cY + 0.16, w: 0.65, h: 0.76,
      fontSize: 46, fontFace: FONT, color: st.color, bold: true, margin: 0,
    });
    s.addText(st.heading, {
      x: x + 0.2, y: cY + 1.02, w: cW - 0.32, h: 0.5,
      fontSize: 15, fontFace: FONT, color: C.white, bold: true, margin: 0,
    });
    s.addText(st.body, {
      x: x + 0.2, y: cY + 1.58, w: cW - 0.32, h: 1.0,
      fontSize: 11, fontFace: FONT, color: C.muted, margin: 0,
    });

    // Example box
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.14, y: cY + 2.72, w: cW - 0.28, h: 0.5,
      fill: { color: C.bg }, line: { color: st.color, width: 1 },
    });
    s.addText(st.example, {
      x: x + 0.22, y: cY + 2.76, w: cW - 0.44, h: 0.42,
      fontSize: 9.5, fontFace: FONT, color: st.color,
      italic: true, valign: "middle", margin: 0,
    });

    // Arrow between cards
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.LINE, {
        x: x + cW, y: cY + cH / 2, w: gap, h: 0,
        line: { color: C.cyan, width: 1.5 },
      });
    }
  });
}

// ─── SLIDE 7: MARKET SIZE ─────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Market Opportunity");
  title(s, "A Platform-Sized Market");
  sub(s, "Waypoint sits at the intersection of automation, AI, and knowledge sharing.");
  divider(s);

  const markets = [
    {
      size: "$13B",  label: "RPA Market Today",
      detail: "Robotic Process Automation\nProjected $50B+ by 2030",
      color: C.cyan,
    },
    {
      size: "$30B+", label: "Knowledge Sharing Tools",
      detail: "Notion, Loom, Confluence and\ntheir $20B+ combined market",
      color: C.purple,
    },
    {
      size: "40%",   label: "Of Work Hours Wasted",
      detail: "Knowledge workers spend\nnearly half their time on\nrepetitive web tasks",
      color: C.orange,
    },
  ];

  const cW = 2.9, cH = 2.85, cY = 1.82, gap = 0.17;
  markets.forEach((m, i) => {
    const x = 0.5 + i * (cW + gap);
    card(s, x, cY, cW, cH, { accent: m.color });

    s.addText(m.size, {
      x: x + 0.18, y: cY + 0.18, w: cW - 0.28, h: 0.95,
      fontSize: 50, fontFace: FONT, color: m.color, bold: true, margin: 0,
    });
    s.addText(m.label, {
      x: x + 0.18, y: cY + 1.18, w: cW - 0.28, h: 0.38,
      fontSize: 13.5, fontFace: FONT, color: C.white, bold: true, margin: 0,
    });
    s.addText(m.detail, {
      x: x + 0.18, y: cY + 1.62, w: cW - 0.28, h: 0.95,
      fontSize: 11, fontFace: FONT, color: C.muted, margin: 0,
    });
  });
}

// ─── SLIDE 8: COMPETITIVE LANDSCAPE ──────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Competitive Landscape");
  title(s, "No One Else Closes the Loop");

  const headers = ["", "Waypoint", "Zapier", "MultiOn", "Operator (OpenAI)", "Loom"];
  const rows = [
    ["Natural language input",   "Y", "N", "Y", "Y", "N"],
    ["Works on any website",     "Y", "N", "Y", "Y", "N"],
    ["Real browser (not API)",   "Y", "N", "Y", "Y", "N"],
    ["Shareable result links",   "Y", "N", "N", "N", "Y"],
    ["Live activity trace",      "Y", "N", "N", "N", "N"],
    ["Human-in-the-loop",        "Y", "N", "N", "N", "N"],
    ["Network effects / viral",  "Y", "N", "N", "N", "Y"],
  ];

  const colW = [2.6, 1.18, 1.18, 1.18, 1.44, 1.08];
  const rH = 0.42, tX = 0.36, tY = 1.42;

  // Header row
  let xOff = tX;
  headers.forEach((h, ci) => {
    const isWP = ci === 1;
    s.addShape(pres.shapes.RECTANGLE, {
      x: xOff, y: tY, w: colW[ci], h: rH,
      fill: { color: isWP ? C.cyan : "0D1F35" }, line: { color: C.dim, width: 0.5 },
    });
    s.addText(h, {
      x: xOff + 0.05, y: tY, w: colW[ci] - 0.1, h: rH,
      fontSize: isWP ? 11 : 9.5, fontFace: FONT,
      color: isWP ? C.bg : C.muted,
      bold: true, align: "center", valign: "middle", margin: 0,
    });
    xOff += colW[ci];
  });

  // Data rows
  rows.forEach((row, ri) => {
    let xOff = tX;
    const ry = tY + (ri + 1) * rH;
    const even = ri % 2 === 0;

    row.forEach((cell, ci) => {
      const isWP = ci === 1;
      const isFeature = ci === 0;
      const isYes = cell === "Y";
      const isNo  = cell === "N";

      s.addShape(pres.shapes.RECTANGLE, {
        x: xOff, y: ry, w: colW[ci], h: rH,
        fill: { color: isWP ? "071B2E" : (even ? C.bgCard : C.bgMid) },
        line: { color: C.dim, width: 0.5 },
      });

      let txt = cell;
      let fc = C.muted;
      let fs = 11;
      let fw = false;
      let fa = "center";

      if (isFeature) { fc = C.white; fa = "left"; }
      else if (isYes && isWP) { txt = "Y"; fc = C.cyan; fs = 13; fw = true; }
      else if (isYes) { txt = "Y"; fc = C.green; fs = 13; fw = true; }
      else if (isNo)  { txt = "N"; fc = C.red;   fs = 13; fw = true; }

      s.addText(txt, {
        x: xOff + (isFeature ? 0.1 : 0), y: ry,
        w: colW[ci] - (isFeature ? 0.1 : 0), h: rH,
        fontSize: fs, fontFace: FONT, color: fc,
        bold: fw, align: fa, valign: "middle", margin: 0,
      });
      xOff += colW[ci];
    });
  });

  s.addText("Waypoint is the only AI browser agent with a social sharing layer — creating network effects and viral distribution.", {
    x: 0.36, y: 5.2, w: 9.3, h: 0.28,
    fontSize: 10, fontFace: FONT, color: C.muted, italic: true, align: "center", margin: 0,
  });
}

// ─── SLIDE 9: BUSINESS MODEL ──────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Business Model");
  title(s, "Multiple Monetization Layers");
  sub(s, "Starting with usage-based pricing, growing into enterprise and API.");
  divider(s);

  const tiers = [
    {
      name: "Free", price: "$0", sub: "per month", color: C.muted, highlight: false,
      features: [
        "10 automations / month",
        "Public shareable links",
        "Full activity trace",
        "No account to view results",
      ],
      badge: "Growth driver",
    },
    {
      name: "Pro", price: "$29", sub: "per month", color: C.cyan, highlight: true,
      features: [
        "Unlimited automations",
        "Private & team-only links",
        "Priority execution speed",
        "Longer automation chains",
      ],
      badge: "Core revenue",
    },
    {
      name: "Enterprise", price: "Custom", sub: "annual contract", color: C.purple, highlight: false,
      features: [
        "Private browser fleet",
        "SSO & audit logs",
        "API access for developers",
        "SLA & dedicated support",
      ],
      badge: "Expansion revenue",
    },
  ];

  const cW = 2.9, cH = 3.2, cY = 1.82, gap = 0.17;
  tiers.forEach((t, i) => {
    const x = 0.5 + i * (cW + gap);

    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: cH,
      fill: { color: t.highlight ? "071E36" : C.bgCard },
      line: { color: t.highlight ? C.cyan : C.dim, width: t.highlight ? 2 : 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: 0.06,
      fill: { color: t.color }, line: { color: t.color, width: 0 },
    });

    s.addText(t.name, {
      x: x + 0.2, y: cY + 0.17, w: cW - 0.3, h: 0.38,
      fontSize: 16, fontFace: FONT, color: t.color, bold: true, margin: 0,
    });
    s.addText(t.price, {
      x: x + 0.2, y: cY + 0.57, w: cW - 0.3, h: 0.72,
      fontSize: 40, fontFace: FONT, color: C.white, bold: true, margin: 0,
    });
    s.addText(t.sub, {
      x: x + 0.2, y: cY + 1.3, w: cW - 0.3, h: 0.28,
      fontSize: 11, fontFace: FONT, color: C.muted, margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.2, y: cY + 1.63, w: cW - 0.4, h: 0.014,
      fill: { color: C.dim }, line: { color: C.dim, width: 0 },
    });

    t.features.forEach((feat, fi) => {
      s.addText([
        { text: "->  ", options: { color: t.color, bold: true } },
        { text: feat, options: { color: C.white } },
      ], {
        x: x + 0.2, y: cY + 1.72 + fi * 0.32, w: cW - 0.3, h: 0.28,
        fontSize: 10.5, fontFace: FONT, margin: 0,
      });
    });

    // Badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.2, y: cY + 2.9, w: cW - 0.4, h: 0.22,
      fill: { color: t.highlight ? C.cyan : C.bgMid },
      line: { color: t.color, width: 0 },
    });
    s.addText(t.badge, {
      x: x + 0.2, y: cY + 2.9, w: cW - 0.4, h: 0.22,
      fontSize: 9.5, fontFace: FONT,
      color: t.highlight ? C.bg : t.color,
      bold: true, align: "center", valign: "middle", margin: 0,
    });
  });
}

// ─── SLIDE 10: TRACTION & ROADMAP ────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Traction & Roadmap");
  title(s, "Built. Shipping. Scaling.");
  sub(s, "We have a working product. Here is what is done and what comes next.");
  divider(s);

  const cols = [
    {
      status: "Done", color: C.green,
      items: [
        "Full AI browser agent (Gemini + Playwright)",
        "Natural language task execution",
        "Live activity trace & screenshots",
        "Shareable result links",
        "Human-in-the-loop for CAPTCHAs",
      ],
    },
    {
      status: "Now", color: C.cyan,
      items: [
        "Production deployment (Render)",
        "Beta user onboarding",
        "Complex UI handling (dropdowns, forms)",
        "Reliability & performance hardening",
      ],
    },
    {
      status: "Next", color: C.purple,
      items: [
        "Pro & Enterprise tier launch",
        "Developer API",
        "Team workspaces & private links",
        "Scheduled / recurring automations",
      ],
    },
  ];

  const cW = 2.9, cH = 3.1, cY = 1.82, gap = 0.17;
  cols.forEach((col, i) => {
    const x = 0.5 + i * (cW + gap);
    card(s, x, cY, cW, cH, { accent: col.color });

    // Status badge
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.18, y: cY + 0.15, w: 0.78, h: 0.3,
      fill: { color: col.color }, line: { color: col.color, width: 0 },
    });
    s.addText(col.status, {
      x: x + 0.18, y: cY + 0.15, w: 0.78, h: 0.3,
      fontSize: 10, fontFace: FONT, color: C.bg,
      bold: true, align: "center", valign: "middle", margin: 0,
    });

    col.items.forEach((item, ii) => {
      s.addText([
        { text: "  ", options: { color: col.color, bold: true } },
        { text: item, options: { color: C.white } },
      ], {
        x: x + 0.18, y: cY + 0.6 + ii * 0.5, w: cW - 0.28, h: 0.44,
        fontSize: 10.5, fontFace: FONT, margin: 0,
      });
    });
  });
}

// ─── SLIDE 11: TEAM ───────────────────────────────────────────────────────────
{
  const s = mkSlide();
  label(s, "Team");
  title(s, "The Team");
  sub(s, "Built by people obsessed with making automation accessible to everyone.");
  divider(s);

  const members = [
    { role: "Co-Founder / CEO",  focus: "Product, Vision, GTM",     bg: "Strategy  |  Fundraising  |  Growth" },
    { role: "Co-Founder / CTO",  focus: "Engineering, AI, Infra",   bg: "Playwright  |  Gemini  |  FastAPI" },
    { role: "Advisor",           focus: "Industry & Domain Expert",  bg: "Network  |  Customers  |  Partnerships" },
  ];

  const cW = 2.9, cH = 2.88, cY = 1.82, gap = 0.17;
  members.forEach((m, i) => {
    const x = 0.5 + i * (cW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: cH,
      fill: { color: C.bgCard }, line: { color: C.dim, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cY, w: cW, h: 0.06,
      fill: { color: C.cyan }, line: { color: C.cyan, width: 0 },
    });

    // Avatar circle
    s.addShape(pres.shapes.OVAL, {
      x: x + (cW / 2) - 0.58, y: cY + 0.2, w: 1.16, h: 1.16,
      fill: { color: C.bgMid }, line: { color: C.cyan, width: 2 },
    });
    s.addText("?", {
      x: x + (cW / 2) - 0.58, y: cY + 0.2, w: 1.16, h: 1.16,
      fontSize: 36, fontFace: FONT, color: C.dim,
      align: "center", valign: "middle", bold: true, margin: 0,
    });

    s.addText(m.role, {
      x: x + 0.15, y: cY + 1.5, w: cW - 0.3, h: 0.38,
      fontSize: 13, fontFace: FONT, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(m.focus, {
      x: x + 0.15, y: cY + 1.9, w: cW - 0.3, h: 0.3,
      fontSize: 11, fontFace: FONT, color: C.cyan, align: "center", margin: 0,
    });
    s.addText(m.bg, {
      x: x + 0.15, y: cY + 2.28, w: cW - 0.3, h: 0.45,
      fontSize: 10, fontFace: FONT, color: C.muted, align: "center", italic: true, margin: 0,
    });
  });
}

// ─── SLIDE 12: THE ASK ────────────────────────────────────────────────────────
{
  const s = mkSlide(C.bgDeep);

  // Glow accents
  s.addShape(pres.shapes.OVAL, {
    x: -1.5, y: -1.5, w: 5, h: 5,
    fill: { color: "00C8FF", transparency: 90 }, line: { color: "00C8FF", width: 0 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: 7.5, y: 2.2, w: 5, h: 5,
    fill: { color: "7B61FF", transparency: 90 }, line: { color: "7B61FF", width: 0 },
  });

  s.addText("THE ASK", {
    x: 0.5, y: 0.35, w: 9, h: 0.38,
    fontSize: 10, fontFace: FONT, color: C.cyan,
    bold: true, charSpacing: 6, align: "center", margin: 0,
  });
  s.addText("Raising a Pre-Seed Round", {
    x: 0.5, y: 0.8, w: 9, h: 0.75,
    fontSize: 36, fontFace: FONT, color: C.white, bold: true, align: "center", margin: 0,
  });

  // Amount oval
  s.addShape(pres.shapes.OVAL, {
    x: 3.4, y: 1.68, w: 3.2, h: 1.05,
    fill: { color: "00C8FF", transparency: 88 }, line: { color: C.cyan, width: 2 },
  });
  s.addText("$X00K", {
    x: 3.4, y: 1.68, w: 3.2, h: 1.05,
    fontSize: 40, fontFace: FONT, color: C.cyan,
    bold: true, align: "center", valign: "middle", margin: 0,
  });

  // Use of funds
  const uses = [
    { pct: "40%", label: "Engineering",    detail: "Agent reliability, new integrations" },
    { pct: "30%", label: "Infrastructure", detail: "Browser fleet, scale, uptime" },
    { pct: "20%", label: "Growth & GTM",   detail: "User acquisition, partnerships" },
    { pct: "10%", label: "Operations",     detail: "Legal, admin, tooling" },
  ];

  const uW = 2.15, uH = 1.38, uY = 3.02;
  uses.forEach((u, i) => {
    const x = 0.5 + i * (uW + 0.2);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: uY, w: uW, h: uH,
      fill: { color: "0F2040" }, line: { color: C.dim, width: 1 },
    });
    s.addText(u.pct, {
      x, y: uY + 0.1, w: uW, h: 0.56,
      fontSize: 30, fontFace: FONT, color: C.cyan, bold: true, align: "center", margin: 0,
    });
    s.addText(u.label, {
      x, y: uY + 0.7, w: uW, h: 0.3,
      fontSize: 11, fontFace: FONT, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(u.detail, {
      x, y: uY + 1.01, w: uW, h: 0.3,
      fontSize: 9.5, fontFace: FONT, color: C.muted, align: "center", margin: 0,
    });
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.6, w: 9, h: 0.015,
    fill: { color: C.dim }, line: { color: C.dim, width: 0 },
  });
  s.addText("waypoint.app  |  hello@waypoint.app", {
    x: 0.5, y: 4.7, w: 9, h: 0.3,
    fontSize: 11, fontFace: FONT, color: C.muted, align: "center", margin: 0,
  });
}

// ─── WRITE FILE ───────────────────────────────────────────────────────────────
const OUTPUT = "C:\\Users\\start\\Waypoint\\Waypoint_Pitch_Deck.pptx";

pres.writeFile({ fileName: OUTPUT })
  .then(() => console.log("Done: " + OUTPUT))
  .catch(err => { console.error("Error:", err); process.exit(1); });
