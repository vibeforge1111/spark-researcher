# Web Design Bench Promotion Bridge

## Benchmark Metrics

- `web_design_score`: blended outcome metric
- `award_signal_score`: likelihood the system feels compositionally strong and distinctive
- `ux_system_score`: information hierarchy, clarity, and task coherence
- `interaction_craft_score`: quality of motion, transitions, and interface state design
- `conversion_clarity_score`: strength of the path from interest to action
- `accessibility_safety_score`: resilience across motion, contrast, keyboard, and inclusive use
- `verdict_confidence`: evaluator certainty

## Promotion Thresholds

### Advisory

Default state.
Do not promote.

Typical conditions:

- `web_design_score < 0.66`
- or `accessibility_safety_score < 0.54`
- or `ux_system_score < 0.56`

### Candidate

Good enough to keep studying.

Required minimums:

- `web_design_score >= 0.66`
- `ux_system_score >= 0.56`
- `accessibility_safety_score >= 0.54`

### Validated

Strong enough for doctrine candidate status.

Required minimums:

- `web_design_score >= 0.80`
- `ux_system_score >= 0.68`
- `conversion_clarity_score >= 0.62`
- `accessibility_safety_score >= 0.70`

## Promotion Rule

No design system is promoted on award signal alone.

High `award_signal_score` with weak accessibility or conversion should be treated as a warning, not a win.

## Real-World Bridge

Before long-lived doctrine promotion, check the design direction against at least one live surface:

- landing page conversion
- demo-start rate
- usability session success
- dashboard task completion
- qualitative confusion signals
- accessibility audit outcomes
