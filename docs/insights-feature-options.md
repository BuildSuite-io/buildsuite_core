# Insights — Feature Overview & Implementation Options

*A plain-language brief on what the Insights feature is, and the choices for building it in the live product.*

---

## What Insights is

Insights is an **ask-a-question reporting tool**. Instead of hunting through menus for the right report, a user types a plain question — *"supplier bill value by supplier, top 8"* or *"tasks by status"* — and gets a live chart or table built from the company's own data. They can then reshape it with a follow-up ("…as a pie", "…for the Bangalore project", "…last month") or switch the chart type.

The demo already covers roughly **20 areas of the business** — projects, tasks, stages, purchase orders, receipts, site consumption, work orders, measurement books, invoices, supplier bills, expenses, petty cash, attendance, machinery usage, and more — and ships with a set of ready-made starter questions so a first-time user isn't staring at an empty box.

**Every number shown comes from a real record.** If the tool doesn't understand a question, it says so rather than guessing — an important trust property.

---

## The good news: the hard part is already designed

The prototype was built in two clean halves:

1. **The "understanding" half** — turns a typed question into a precise, structured request (which data, what to measure, how to group it, what chart).
2. **The "engine" half** — takes that structured request and produces the actual numbers and chart from the live data.

These two halves are deliberately kept separate. That means **the engine, the ~20 data areas, and the charts can be reused almost as-is** — the only piece that changes between "demo" and "production" is *how the question is understood*. This significantly lowers the cost and risk of building the real thing.

---

## The choices to make

There are four independent decisions. None of them lock the others.

### 1. How questions are understood

| Approach | What it means | Strengths | Trade-offs |
|---|---|---|---|
| **Rules-based (as in the demo)** | A built-in dictionary of terms maps the question to a request | Free to run, instant, private, never invents an answer | Understands common phrasings only; new wordings need to be added over time |
| **AI-powered (e.g. Claude)** | An AI model reads the question and produces the structured request | Understands almost any phrasing and natural follow-ups | Small per-question cost + a moment's delay; needs guardrails so it stays inside real data; data-handling review |
| **Both (recommended)** | Rules first; the AI only steps in when the rules don't recognise a question | Most questions answered instantly and free; AI covers the rest | Two paths to maintain |

> The demo's design was purpose-built so an AI model can be **added later without rebuilding anything else**.

### 2. Where the number-crunching happens

| Approach | What it means | Best for |
|---|---|---|
| **In the browser** | Reuse the demo's engine directly, feeding it live data | Fastest to launch; ideal for smaller data (masters, small lists) |
| **On the server** | The database does the grouping and totalling, returning only the summary | Large, transaction-heavy data (invoices, bills, receipts); scales better; enforces access rules natively |
| **Adopt a ready-made BI tool** | Use an off-the-shelf business-intelligence product | Teams wanting full dashboards; heavier to set up and align with the existing look and permissions |

A sensible default is **browser for small data, server for the heavy data.**

### 3. The charts

The demo uses clean, custom-built charts. We can **keep them exactly** (preserves the polished look) or switch to a standard charting library to reduce long-term upkeep. This is a low-stakes choice.

### 4. Who can use it, and what's in the first release

- **Access**: today it's limited to leadership roles (owner, director, project manager, admin). Every data area also respects each person's existing permissions — people only ever see numbers they're already allowed to see.
- **Scope**: we can launch with a focused first set of data areas and grow from there.

---

## Recommended path

1. **Reuse** the demo's engine, data areas, and charts — the bulk of the work is already done and battle-tested in the prototype.
2. **Launch** with the rules-based understanding (no external dependency, quickest to production) connected to live data.
3. **Grow** into server-side crunching for the heavy datasets as usage scales.
4. **Add AI understanding (Claude) as a fallback** once the base is proven — so the AI is a helpful extra, never a single point of failure.

This mirrors the exact design the prototype was built around, and keeps the AI piece **additive and low-risk**.

---

## Phasing at a glance

| Phase | What ships | Understanding | Data |
|---|---|---|---|
| **1 — MVP** | A focused set of data areas, core charts, starter questions | Rules-based | Live data (browser) |
| **2 — Scale** | Remaining data areas, detail-table views, refine & chart-switcher | Rules-based | + Server-side for heavy data |
| **3 — Natural language** | "Ask anything" quality | + AI (Claude) fallback | — |
| **4 — Assistant** | Guided tours + an in-app ask box that reuses the same engine | — | — |

---

## Two things to decide before building

1. **Which data areas make the first release?** (We'd recommend the highest-value few rather than all 20 at once.)
2. **Default crunching location** — browser vs server. Our lean: server for transaction-heavy data, browser for small reference data.

---

*Prepared as a research brief. No development has started; this document exists to align on approach before any build.*
