# Pokemon Player One-Loop Spec

The Pokemon player chip should eventually run one governing loop with these stages:

1. emulator readiness check
2. save-state readiness check
3. bounded policy evaluation
4. packet promotion
5. frontier suggestion
6. memory and watchtower refresh
7. outer validation queueing for richer tasks

## Current Inner Truth Surface

Right now the inner truth surface is shallow but real:

- emulator-connected runs
- screen novelty
- action diversity
- interaction coverage

This is enough to connect Spark to real Pokemon play.
It is not enough to claim route mastery or battle mastery.

## Next Benchmark Shape

The next useful benchmark surface should be save-state-backed tasks such as:

- leave the opening room
- navigate to a target tile
- clear the opening text quickly
- perform a menu fastpath cleanly
- open and close menus without stalling
- reach a specific NPC
- win a simple scripted battle

## Promotion Rule

Do not promote high-level Pokemon speedrun doctrine from cold-boot wandering alone.
Require repeatable save-state-backed task wins and route-study evidence before treating a policy as grounded doctrine.
