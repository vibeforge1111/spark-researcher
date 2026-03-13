# domain-chip-vibe-incubator

`domain-chip-vibe-incubator` is a Spark domain chip for running a lean incubator that launches and compounds vibe-coded startups with agentic workflows.

This chip is designed for the constraint set where:

- one operator is carrying most of the system
- agentic frameworks replace missing headcount
- capital efficiency matters
- real-world usefulness matters more than incubator theater
- trust, resilience, and operational review matter after a painful failure cycle

The current version is an honest fixed-evaluator scaffold, not a live benchmark.
It is meant to help choose and pressure-test venture operating motions before those motions graduate into real launches, paying pilots, and portfolio doctrine.

## What It Scores

The chip evaluates candidate incubator plays across:

- `incubator_compound_score`
- `solo_operator_fit_score`
- `distribution_leverage_score`
- `automation_leverage_score`
- `portfolio_learning_score`
- `revenue_readiness_score`
- `resilience_score`
- `verdict_confidence`

The `ops` loop also emits:

- `ops_portfolio_focus_score`
- `ops_automation_coverage_score`
- `ops_review_hygiene_score`
- `ops_validation_velocity_score`
- `ops_trust_hygiene_score`
- `ops_knowledge_capture_score`

The control plane also drives a venture execution layer with:

- scout intake and admissions review
- customer conversation and pipeline logging
- trust review, data-room tracking, and investor targeting
- portfolio retrospectives and reusable asset capture
- experiment logs
- build request logs
- KPI snapshots
- derived venture task packets
- doctrine and failure watchtower pages

## Candidate Unit

The main candidate unit is:

- `venture_model`
- `customer_surface`
- `distribution_engine`
- `build_stack`
- `validation_motion`
- `trust_model`
- `operating_cadence`
- `venture_theme`

This keeps the chip focused on real incubator leverage, not vague startup taste.

## Current Truth Surface

- the evaluator is deterministic and heuristic
- `comparison_class` is `heuristic_frontier`
- fixed-evaluator evidence can influence incubator doctrine candidates
- real doctrine still needs live venture proof, paying users, and operator review

## Validation

From the repo root:

```powershell
$env:PYTHONPATH = "src"
python -m spark_researcher.cli chips validate --config domain-chip-vibe-incubator/spark-researcher.project.json
python -m spark_researcher.cli run --config domain-chip-vibe-incubator/spark-researcher.project.json --command research --candidate-id global-baseline
python -m spark_researcher.cli run --config domain-chip-vibe-incubator/spark-researcher.project.json --command research --candidate-id founder-backoffice-studio
python -m spark_researcher.cli run --config domain-chip-vibe-incubator/spark-researcher.project.json --command ops --candidate-id ops-baseline
python -m spark_researcher.cli run --config domain-chip-vibe-incubator/spark-researcher.project.json --command ops --candidate-id ops-tight-three-lane
python -m spark_researcher.cli candidates suggest --config domain-chip-vibe-incubator/spark-researcher.project.json --command research
python -m spark_researcher.cli candidates suggest --config domain-chip-vibe-incubator/spark-researcher.project.json --command ops
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py status
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py scout-intake --application-id scout-founder-os --label "Founder OS concierge" --founder-id operator-a --entry-source referral --venture-model agentic_saas --customer-surface founder_backoffice --distribution-engine operator_content --venture-theme "founder os concierge"
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py admissions-review --application-id scout-founder-os --decision invite
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py customer-conversation --venture-id founder-backoffice-studio --conversation-id call-001 --customer-label "Founder A" --channel call --stage discovery --willingness-to-pay maybe --objection "Needs deeper CRM automation"
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py pipeline-opportunity --venture-id founder-backoffice-studio --opportunity-id opp-001 --customer-label "Founder A" --source referral --stage qualified --status open --value 1200 --confidence 0.7
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py trust-review --venture-id founder-backoffice-studio --review-id trust-001 --scope automation_release --status green --risk-area release_safety
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py data-room-item --venture-id founder-backoffice-studio --item-id deck-v1 --category deck --label "Investor deck" --status ready
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py investor-target --venture-id founder-backoffice-studio --target-id investor-001 --investor-label "Operator Angels" --thesis-fit high --stage targeted --status open
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py portfolio-retrospective --venture-id founder-backoffice-studio --retrospective-id retro-001 --scope weekly_review --outcome win --lesson "Lead with ROI packet before workflow tour." --doctrine-claim "Founder backoffice demos work better when the ROI packet comes before the product tour." --boundary "Use this only when the founder already feels painful follow-up or CRM chaos." --promote-doctrine --evidence-strength high --reusable-asset-id roi-packet-template
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py reusable-asset --venture-id founder-backoffice-studio --asset-id roi-packet-template --label "Founder ROI packet template" --kind playbook --status shared --reused-by-count 2 --shared-surface sales_demo
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py experiment --venture-id founder-backoffice-studio --experiment-id paid-sprint-1 --hypothesis "A direct founder pain landing page converts paid design partner calls" --status running --target-metric paid_signals
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py build-request --venture-id founder-backoffice-studio --request-id crm-automation --title "Automate founder CRM follow-up" --kind workflow --priority high
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py kpi-snapshot --venture-id founder-backoffice-studio --customer-conversations 5 --paid-signals 2 --weekly-revenue 500 --pipeline-count 7 --active-users 3 --automation-coverage 0.76
python -m spark_researcher.cli memory sync --config domain-chip-vibe-incubator/spark-researcher.project.json
python -m spark_researcher.cli obsidian build --config domain-chip-vibe-incubator/spark-researcher.project.json
python -m spark_researcher.cli summary --config domain-chip-vibe-incubator/spark-researcher.project.json
```

## Real-World Validation

The chip should only earn stronger trust when it proves:

- faster launch cycles without hidden chaos
- paying validation or real usage
- reusable assets across multiple ventures
- security and trust discipline that survives real-world stress

See:

- `docs/VIBE_INCUBATOR_ONE_LOOP_SPEC.md`
- `docs/VIBE_INCUBATOR_REALWORLD_EVAL.md`
- `docs/VIBE_INCUBATOR_SOURCE_MAP.md`
- `docs/VIBE_INCUBATOR_OS_ARCHITECTURE.md`
- `docs/VIBE_INCUBATOR_ARCHITECTURE_PACKET.json`
- `docs/VIBE_INCUBATOR_AUTOLOOP.md`
- `docs/VIBE_INCUBATOR_CONTROL_PLANE.md`
