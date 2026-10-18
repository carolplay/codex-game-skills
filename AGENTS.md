# WOS agent bot workspace

- Public, reusable game skills live in `skills/`.
- Machine-local account settings, execution records and experiments live in `local-data/`, which is Git-ignored. Never commit that directory or copy private account data into public skills.
- Read `local-data/README.md` for local paths and operating state when the directory exists.
- The CrossMacro source repository is a separate project folder. Runtime dependencies and machine-specific launcher configuration live outside Git.
- Preserve the existing pause state; filesystem maintenance does not authorize game actions or resuming schedules.
- New WOS automation uses `skills/play-whiteout-survival-macros/` and its fixed visit plan. The unchanged `skills/play-whiteout-survival/` is V1 pure-agent knowledge/fallback. Read only the relevant references and current run checkpoint, rather than accumulating old prompts.

- Preserve task composability: declare fixed entry/exit anchors, explicit business dependencies and bounded page-specific exits. A business deviation may continue only after local anchor verification; identity, permissions, lock or window-size failures stop the whole batch. Never use agent fallback to finish daily tasks.
- Maintain `skills/play-whiteout-survival-macros/references/visit-plan.md` as the task backlog: status is 不知道要不要做 / 没做 / 已做 / 已验证; keep the current linear macro action list and state the verified branch/role scope.
- Main-account status is machine-local and must be honored. Use only explicitly marked test roles for new macro development; permission for a main account to finish an already-started batch does not make it a test role. Prefer targeted validation of new or changed actions over repeating stable full batches.

- Read `docs/PROJECT-CONTEXT.md` for user authorization and the low-cost game-resource experiment model. Do not add repeated project-level approvals for already-authorized game actions or treat virtual resources as real money. Game strategy belongs to the visit plan/local role configuration; system permissions and real payment remain separate. This does not override platform-enforced review, account scope, pause state or the no-payment boundary.

- Use 三班 (UTC00/08/16) terminology and classify tasks by shift/day/week/four-week/event. Read `docs/V2-OPERATIONS.md` for pilot and fresh V2 worker boundaries. At the next user discussion, raise `docs/RESOURCE-TASK-PRIORITIES.md`; that discussion must not reduce daily coverage.
