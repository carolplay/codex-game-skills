# WOS agent bot workspace

- Public, reusable game skills live in `skills/`.
- Machine-local account settings, execution records and experiments live in `local-data/`, which is Git-ignored. Never commit that directory or copy private account data into public skills.
- Read `local-data/README.md` for local paths and operating state when the directory exists.
- The CrossMacro source repository is a separate project folder. Runtime dependencies and machine-specific launcher configuration live outside Git.
- Preserve the existing pause state; filesystem maintenance does not authorize game actions or resuming schedules.
- New WOS automation uses `skills/play-whiteout-survival-macros/` and its fixed visit plan. The unchanged `skills/play-whiteout-survival/` is V1 pure-agent knowledge/fallback. Read only the relevant references and current run checkpoint, rather than accumulating old prompts.
