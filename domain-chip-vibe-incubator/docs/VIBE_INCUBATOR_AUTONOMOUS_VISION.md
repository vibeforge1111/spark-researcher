# Vibe Incubator: Autonomous Vision & Strategy

## Mission

Build an autonomous incubator operating system where a solo operator — amplified by specialized AI agents — can discover, evaluate, coach, and grow early-stage startups with the rigor of YC, the mentorship density of Techstars, and the data-driven precision of 500 Global, all running continuously without manual invocation.

## What "Best" Means

| Dimension | World-Class Human Incubator | Our Agentic Target |
|-----------|---------------------------|-------------------|
| **Selection** | YC reads 30k apps, invites 1.5% | Agent-scored intake, portfolio-fit analysis, always-open rolling admissions |
| **Coaching cadence** | Techstars: daily standups + weekly mentor sessions | Continuous: agents monitor KPIs every tick, coach async via structured prompts |
| **Kill discipline** | YC: "2 weeks flat = hard conversation" | Auto-detect stale ventures at 7d, auto-escalate at 14d, agent-generated pivot analysis |
| **Market grounding** | Partner networks, domain experts | Real-time enrichment: web search, Twitter signals, competitor tracking |
| **Feedback loops** | Partners learn over decades | System calibrates scoring weights weekly from prediction-vs-outcome data |
| **Demo Day** | One shot, 10-minute pitch | Continuous investor-readiness scoring, auto-generated briefing packets |
| **Governance** | Board votes, LP agreements | Bounded futarchy, transparent proposal/tally system |

## How We Create Value for Startups

```
Founder submits idea
    |
    v
  ADMISSIONS AGENT
  Evaluates: market size, founder fit, portfolio overlap, timing
  Output: invite / waitlist / reject + reasoning
    |  (human gate: final invite decision)
    v
  CONTINUOUS OPERATING SYSTEM
    Every 5 min:  Scheduler ticks -> refresh metrics -> emit events -> agents process queues
    Every day:    Age counters -> stale detection -> enrichment -> coaching prompts
    Every week:   Outcome tracking -> weight calibration -> governance tallies -> digests

  Agents available 24/7:
    Founder Coach      — weekly prep, meeting notes
    Customer Research   — ICP, interview guides
    Build Orchestrator  — task routing, QA
    GTM Operator        — distribution, launch calendar
    Trust Diligence     — security, compliance
    Capital Operator    — investor matching
    Portfolio Librarian — doctrine, pattern library
    |
    v
  Value: faster iteration, data-driven pivots, continuous coaching,
         transparent governance, investor readiness
```

## Methodology Adoptions

### From YC
- Weekly growth metrics with 10% WoW target -> `kpi-snapshot` auto-ingested, trend computed, deviation triggers coaching agent
- Office hours -> Founder Coach agent prepares agenda from KPI deltas, surfaces blockers
- Batch Demo Day -> Continuous investor readiness score; Capital Operator generates briefing packets on threshold

### From Techstars
- Mentor-driven model -> Agent-as-mentor with persistent venture context
- "Give first" network effects -> Network graph tracks introductions and value flows
- T-score (Team + Technology + Traction + Total Market) -> Baked into scoring matrix

### From Antler
- Co-founder matching -> Agent-assisted complementary skill gap identification
- "People before ideas" -> Founder quality weighted higher in early stages

### From Entrepreneur First
- Edge Framework (technical + domain + conviction) -> Mapped to build_stack, customer_surface, distribution_engine
- Pre-team formation -> Application stage tracking with structured founder interviews

### From Pioneer
- Automated tournament evaluation -> Compound score ranking across portfolio
- Peer feedback loops -> Cross-venture knowledge sharing via Portfolio Librarian

### From 500 Global
- Data-driven zones (green/yellow/red) -> Trust review status with agent-driven transitions
- Programmatic support -> Queue-based agent dispatch scales linearly

### From DAO Incubators
- Transparent governance -> Proposal/vote/tally system (already built)
- Token-aligned incentives -> SPARK token stack: contribution-earned, not speculation-first

## Implementation Tiers

| Tier | What | Status |
|------|------|--------|
| 1. Event Loop & Scheduler | System runs continuously | Done |
| 2. LLM Decision Agents | Claude-powered reasoning | Done |
| 3. Communication & Notifications | Push alerts to humans | Next |
| 4. External Data Ingestion | Market reality grounding | Planned |
| 5. Feedback & Adaptation | Self-improving scoring | Planned |
| 6. Multi-Agent Orchestration | Specialized agent teams | Planned |

## Design Principles

1. **File-based persistence** — JSON/JSONL works for <50 ventures. No DB migration needed.
2. **Spark hook protocol preserved** — LLM agents called inside hooks, not replacing them.
3. **Blended scoring (60% LLM / 40% heuristic)** — prevents hallucination-driven miscalibration.
4. **Graceful degradation** — no API key? Falls back to current behavior.
5. **Human gates maintained** — 7 decision types always require human approval:
   - Admission invite/reject
   - Venture kill decisions
   - Equity/legal commitments
   - Investor introductions
   - Public commitments
   - Trust escalations (red status)
   - Treasury disbursements
