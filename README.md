# Spark Researcher

Spark Researcher is a small local system for improving a project step by step.

In plain English:

- you tell it what command to run
- it measures the result with a fixed score
- it keeps a log of what happened
- it saves useful lessons
- it can suggest the next experiments
- it can prepare code changes for review without auto-applying them

It is built for people who want something more disciplined than "ask an AI and hope", but much lighter than a full platform.

It started as a blend of two ideas:

- the compactness of Karpathy's `autoresearch`
- Spark Intelligence style recursive loop systems for building real mastery in any domain

From there, it grew a few extra systems around that core:

- domain chips, so domain-specific logic can live outside the kernel
- a collective intelligence network, so useful lessons can be shared as portable capsules
- artifact and memory systems that stay intelligent, inspectable, and human-readable
- bounded self-editing, advisory, and review flows that keep the system useful without turning it into a black box

## What It Feels Like

Think of it as a careful lab assistant for a project.

- it runs tests or project commands
- it records the outcome
- it remembers what seems to work
- it stays reviewable

It is not a hidden agent swarm, not a giant framework, and not an auto-ship black box.

## Who It Is For

Spark Researcher is most useful for people who already have some kind of repeatable task and want to improve it without losing the plot.

- developers who want to test changes against a fixed benchmark or command
- researchers who want a local system that keeps lessons, contradictions, and evidence
- founders or operators who want structured domain learning instead of scattered notes
- prompt or workflow builders who want to compare variants against one score
- people building domain-specific systems who want the core to stay small and readable

## The Basic Flow

```text
You define a project
        |
        v
Spark runs one command
        |
        v
Spark reads one metric
        |
        v
Spark writes the result to the ledger
        |
        v
Spark updates memory and docs
        |
        v
You review what happened
        |
        v
Spark can suggest the next trial
```

## What You Can Use It For

- improving prompts, scripts, or pipelines with a fixed score
- testing small project changes in a repeatable way
- building a system that gets better at a domain over time instead of starting from scratch every session
- organizing research, lessons, and evidence in a way a human can still read on disk
- creating local "memory" that is more useful than chat history but less heavy than a database platform
- keeping an audit trail of what was tried, what failed, and what worked
- generating reviewable self-edit proposals
- running bounded recursive improvement loops without giving up human control
- building domain-specific research or evaluation systems through `domain-chip-*` repos
- sharing portable lessons into a collective intelligence network through capsule exports
- building domain-specific "chips" without bloating the core repo

## Real-Life Use Cases

- Prompt testing:
  You have 20 prompt variants and want to keep testing them against one score instead of guessing from vibes.
- Coding improvement:
  You want a system that proposes code changes, records diffs and logs, and only applies them after review.
- Research memory:
  You are studying a domain like startups, trading, or content, and you want doctrine, boundaries, and contradictions saved in readable files.
- Domain mastery loops:
  You want a system that gets better at one domain over time by combining experiments, memory, and bounded next-step suggestions.
- Benchmark-driven iteration:
  You already have a test, eval, or benchmark and want a simple loop around it instead of building a whole platform.
- Domain chips:
  You want custom logic for one domain without stuffing all that logic into the main repo.

## Why It Exists

Most AI workflows fail in one of two ways:

1. they are too loose, so nobody can tell what actually worked
2. they are too heavy, so the system becomes harder to trust than the project itself

Spark Researcher tries to stay in the middle:

- simple enough to inspect
- strict enough to learn from real results

## Core Ideas

- fixed evaluator, changing strategy
- one experiment at a time
- visible artifacts on disk
- memory stays local and file-first
- self-editing is proposal-first, never silent auto-apply

## Main Pieces

- `run`: run one declared project command
- `loop`: run the current set of candidates
- `autoloop`: run bounded rounds and suggest next trials
- `memory`: save searchable local lessons
- `advisory`: prepare small evidence-backed AI briefs
- `self-edit`: prepare code changes in a copied workspace for review
- `chips`: plug in domain-specific logic without stuffing it into the core

Plain-English translations:

- `advisory`: "give the model only the few local facts that matter"
- `chips`: "keep domain-specific logic in a separate module or repo"
- `collective`: "export portable lessons that another Spark-style system can ingest"

## Self-Edit Flow

```text
You ask for a change
        |
        v
Spark copies the repo to a workspace
        |
        v
An external coding agent edits only that copy
        |
        v
Spark saves diff + logs + request packet
        |
        v
You review the proposal
        |
        +---- reject ----> nothing changes in the repo
        |
        \---- apply -----> Spark copies allowed files back
```

## Quick Start

```powershell
cd C:\Users\USER\Desktop\spark-researcher
python -m pip install -e .
spark-researcher run --command train
spark-researcher loop --command train
spark-researcher autoloop --command train
spark-researcher self-edit propose --prompt "simplify the trainer status output"
```

The bundled config points at [`examples/toy-project/`](examples/toy-project/README.md), so you can run the core loop without setting up a separate project first.

## What A Metric Can Be

A metric is just the score Spark uses to judge whether one trial was better, worse, or unchanged.

Real examples:

- test pass rate
- benchmark accuracy
- error count
- latency
- conversion score
- content engagement quality
- answer quality score from a fixed evaluator
- trading or strategy score

The important part is not the exact metric. The important part is that the system keeps judging trials by the same standard.

## A Simple Mental Model

```text
config -> run -> score -> ledger -> memory -> next decision
```

If you only remember one thing, remember that Spark is trying to make this loop honest and repeatable.

## What You Actually Get

In real use, Spark gives you things you can inspect:

- a ledger of what was tried and what happened
- saved memory documents with lessons and evidence
- self-edit proposal packets with diffs, logs, and request context
- generated watchtower pages in Obsidian
- portable capsule exports for collective sharing

So the output is not just "the AI said this." You get a paper trail.

## What Gets Written

- `artifacts/`: logs, traces, memory exports, self-edit packets, and other generated output
- `obsidian-vault/`: generated watchtower pages
- `.autoresearch/capsules/`: portable capsule exports

Nothing important is hidden behind a database by default.

## Repo Layout

- `src/spark_researcher/`: the runtime
- `docs/`: operator docs and design docs
- `examples/toy-project/`: runnable demo project
- `domain-chip-*`: optional external or sibling domain chips

## Where To Read Next

If you are new:

1. [`docs/README.md`](docs/README.md)
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
3. [`docs/RULES.md`](docs/RULES.md)
4. [`docs/CHECKLOOP.md`](docs/CHECKLOOP.md)

If you want a specific area:

- experiments and bounded automation: [`docs/AUTOLOOP.md`](docs/AUTOLOOP.md)
- memory and saved lessons: [`docs/MEMORY.md`](docs/MEMORY.md)
- evidence-backed AI calls: [`docs/ADVISORY.md`](docs/ADVISORY.md)
- self-edit workflow: [`docs/SELF_EDITING.md`](docs/SELF_EDITING.md)
- external coding backend contract: [`docs/AGENT_BACKENDS.md`](docs/AGENT_BACKENDS.md)
- domain-chip system: [`docs/CHIPS.md`](docs/CHIPS.md)

## Boundaries

Spark Researcher is intentionally opinionated:

- it prefers reviewable files over hidden systems
- it prefers small loops over giant orchestration
- it prefers explicit apply over auto-merge magic
- it prefers local truth over vague "agent memory"

## What It Is Not

- not a chatbot replacement
- not a full workflow orchestration platform
- not an invisible autonomous coding swarm
- not a magic domain expert with no benchmark or evidence
- not a system that should silently edit production code without review

For the full documentation map, use [`docs/README.md`](docs/README.md).
