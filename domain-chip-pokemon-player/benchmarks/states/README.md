# Pokemon Speedrun Save States

Place repeatable benchmark save states in this folder.

Expected filenames:

- `intro_boot.state`
- `leave_bedroom.state`
- `oak_lab_entry.state`
- `text_mash.state`
- `menu_fastpath.state`

Current auto-seed support:

- `intro_boot`
- `leave_bedroom`
- `menu_fastpath`
- `text_mash`

Not yet auto-seeded:

- `oak_lab_entry`

Each state should begin at a stable, benchmarkable scene so task timing and policy quality can be compared honestly across runs.

You can override any of these with task-specific environment variables:

- `POKEMON_TASK_STATE_INTRO_BOOT`
- `POKEMON_TASK_STATE_LEAVE_BEDROOM`
- `POKEMON_TASK_STATE_OAK_LAB_ENTRY`
- `POKEMON_TASK_STATE_TEXT_MASH`
- `POKEMON_TASK_STATE_MENU_FASTPATH`

Or override the state path for a single launch:

```powershell
python -m domain_chip_pokemon_player.play --speedrun-task leave_bedroom --load-state C:\path\to\leave_bedroom.state
```
