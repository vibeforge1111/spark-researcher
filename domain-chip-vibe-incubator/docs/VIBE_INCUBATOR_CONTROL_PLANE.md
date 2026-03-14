# Vibe Vibe Control Plane

Use the control plane to write real operating inputs into the Vibe Vibe state contract.

Run commands from anywhere:

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py status
```

The control plane writes runtime artifacts under `artifacts/incubator_os/`:

- `state.json`
- `latest_tick.json`
- `queue_snapshot.json`
- `scout_snapshot.json`
- `admissions_packets.json`
- `customer_gtm_snapshot.json`
- `customer_signal_packets.json`
- `pipeline_board.json`
- `trust_capital_snapshot.json`
- `trust_review_packets.json`
- `capital_readiness_packets.json`
- `portfolio_learning_snapshot.json`
- `portfolio_doctrine_packets.json`
- `portfolio_failure_registry.json`
- `reusable_asset_registry.json`
- `portfolio_playbook_packets.json`
- `office_hours_packets.json`
- `decision_packets.json`
- `execution_snapshot.json`
- `venture_task_packets.json`
- `admissions.jsonl`
- `scout_applications.jsonl`
- `admission_reviews.jsonl`
- `weekly_updates.jsonl`
- `reviews.jsonl`
- `customer_conversations.jsonl`
- `pipeline_opportunities.jsonl`
- `trust_reviews.jsonl`
- `data_room_items.jsonl`
- `investor_targets.jsonl`
- `portfolio_retrospectives.jsonl`
- `reusable_assets.jsonl`
- `experiments.jsonl`
- `build_requests.jsonl`
- `kpi_snapshots.jsonl`
- `time_passage.jsonl`

## Commands

### Status

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py status
```

### Admit A Venture

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py admit `
  --venture-id local-services-ops-studio `
  --label "Local services ops studio" `
  --founder-id owner `
  --stage qualification `
  --bottleneck model_gap `
  --venture-model service_to_software `
  --customer-surface local_services `
  --distribution-engine warm_outbound
```

### Scout Intake

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py scout-intake `
  --application-id scout-founder-os `
  --label "Founder OS concierge" `
  --founder-id operator-a `
  --founder-label "Operator A" `
  --entry-source referral `
  --venture-model agentic_saas `
  --customer-surface founder_backoffice `
  --distribution-engine operator_content `
  --venture-theme "founder os concierge"
```

This logs a scored scout application and creates a recommendation packet, but it does not admit the venture yet.

### Admissions Review

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py admissions-review `
  --application-id scout-founder-os `
  --decision invite `
  --note "Strong founder fit, ask for sharper paid pilot thesis"
```

Use `--decision admit` to convert a reviewed application into a live venture entry under the portfolio.

### Weekly Update

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py weekly-update `
  --venture-id founder-backoffice-studio `
  --customer-conversations 4 `
  --paid-signals 1 `
  --build-backlog-count 3 `
  --automation-coverage 0.71 `
  --note "Founder update captured"
```

### Review

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py review `
  --venture-id founder-backoffice-studio `
  --decision continue `
  --bottleneck distribution_gap `
  --next-step launch_design_partner_sprint `
  --note "Keep pressure on paid distribution"
```

### Log An Experiment

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py experiment `
  --venture-id founder-backoffice-studio `
  --experiment-id paid-sprint-1 `
  --focus acquisition `
  --hypothesis "A direct founder pain landing page converts paid design partner calls" `
  --status running `
  --target-metric paid_signals `
  --next-step review_copy_and_calls
```

### Queue A Build Request

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py build-request `
  --venture-id founder-backoffice-studio `
  --request-id crm-automation `
  --title "Automate founder CRM follow-up" `
  --kind workflow `
  --priority high `
  --status open `
  --linked-experiment-id paid-sprint-1
```

### Log A Customer Conversation

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py customer-conversation `
  --venture-id founder-backoffice-studio `
  --conversation-id call-001 `
  --customer-label "Founder A" `
  --channel call `
  --stage discovery `
  --willingness-to-pay maybe `
  --objection "Needs deeper CRM automation"
```

### Log A Pipeline Opportunity

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py pipeline-opportunity `
  --venture-id founder-backoffice-studio `
  --opportunity-id opp-001 `
  --customer-label "Founder A" `
  --source referral `
  --stage qualified `
  --status open `
  --value 1200 `
  --confidence 0.7
```

### Log A Trust Review

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py trust-review `
  --venture-id founder-backoffice-studio `
  --review-id trust-001 `
  --scope automation_release `
  --status green `
  --risk-area release_safety `
  --next-step keep_audit_trail_current
```

### Update A Data-Room Item

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py data-room-item `
  --venture-id founder-backoffice-studio `
  --item-id deck-v1 `
  --category deck `
  --label "Investor deck" `
  --status ready
```

### Track An Investor Target

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py investor-target `
  --venture-id founder-backoffice-studio `
  --target-id investor-001 `
  --investor-label "Operator Angels" `
  --thesis-fit high `
  --stage targeted `
  --status open `
  --check-size 100k-250k `
  --next-step draft_intro_packet
```

### Log A Portfolio Retrospective

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py portfolio-retrospective `
  --venture-id founder-backoffice-studio `
  --retrospective-id retro-001 `
  --scope weekly_review `
  --outcome win `
  --lesson "Lead with ROI packet before workflow tour." `
  --doctrine-claim "Founder backoffice demos work better when the ROI packet comes before the product tour." `
  --boundary "Use this only when the founder already feels painful follow-up or CRM chaos." `
  --promote-doctrine `
  --evidence-strength high `
  --reusable-asset-id roi-packet-template `
  --next-step promote_demo_sequence
```

### Capture A Reusable Asset

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py reusable-asset `
  --venture-id founder-backoffice-studio `
  --asset-id roi-packet-template `
  --label "Founder ROI packet template" `
  --kind playbook `
  --status shared `
  --reused-by-count 2 `
  --shared-surface sales_demo `
  --next-step apply_to_internal_os_spinout
```

### Capture A KPI Snapshot

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py kpi-snapshot `
  --venture-id founder-backoffice-studio `
  --customer-conversations 5 `
  --paid-signals 2 `
  --weekly-revenue 500 `
  --pipeline-count 7 `
  --active-users 3 `
  --automation-coverage 0.76 `
  --note "Weekly KPI closeout"
```

### Age The System

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py age --days 3
```

Use `age` to simulate stale updates and review drift in a bounded way.

## Rule

Do not treat the control plane as a background daemon.

- write inputs explicitly
- let the `ops` loop score and route them
- let scouting recommend, but keep admissions review explicit
- use customer conversations and pipeline opportunities to drive validation pressure honestly
- let trust review and capital packets prepare investor readiness, but keep actual intros and decisions human-gated
- use portfolio retrospectives and reusable assets to promote doctrine only when evidence and boundaries are explicit
- use experiments, build requests, and KPI snapshots to create venture task packets
- inspect the vault pages before widening the incubator
