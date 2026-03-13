# Vibe Incubator Control Plane

Use the control plane to write real operating inputs into the incubator state contract.

Run commands from anywhere:

```powershell
python domain-chip-vibe-incubator/src/domain_chip_vibe_incubator/control_plane.py status
```

The control plane writes runtime artifacts under `artifacts/incubator_os/`:

- `state.json`
- `latest_tick.json`
- `queue_snapshot.json`
- `office_hours_packets.json`
- `decision_packets.json`
- `execution_snapshot.json`
- `venture_task_packets.json`
- `admissions.jsonl`
- `weekly_updates.jsonl`
- `reviews.jsonl`
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
- use experiments, build requests, and KPI snapshots to create venture task packets
- inspect the vault pages before widening the incubator
