# WOS agent bot workspace

- Public, reusable game skills live in `skills/`.
- Machine-local account settings, execution records and experiments live in `local-data/`, which is Git-ignored. Never commit that directory or copy private account data into public skills.
- Read `local-data/README.md` for local paths and operating state when the directory exists.
- V3 follows the user-confirmed three-layer architecture: general execution backend + game-specific capability packages + MCP interface. Prove it with WOS first, then expand to Uncharted Waters Online and WoW; see `docs/WOS-V3-NATIVE-RUNTIME.md`. Native permissions and target acceptance precede production migration; MCP is an optional Agent entry, not a per-step model loop.
- The CrossMacro source repository is a separate project folder. Runtime dependencies and machine-specific launcher configuration live outside Git.
- Preserve the existing pause state; filesystem maintenance does not authorize game actions or resuming schedules.
- New WOS automation uses `skills/play-whiteout-survival-macros/` and its fixed visit plan. The unchanged `skills/play-whiteout-survival/` is V1 pure-agent knowledge/fallback. Read only the relevant references and current run checkpoint, rather than accumulating old prompts.

- Preserve task composability: declare fixed entry/exit anchors, explicit business dependencies and bounded page-specific exits. A business deviation may continue only after local anchor verification; identity, permission, lock or window-size failures pause automatic input until the environment is valid again. Game-only recovery, sampling and completion may use the agent when useful; record those separately from macro replay.
- Maintain `skills/play-whiteout-survival-macros/references/visit-plan.md` as the task backlog: status is 不知道要不要做 / 没做 / 已做 / 已验证; keep the current linear macro action list and state the verified branch/role scope.
- The user authorizes all four existing roles, including the main account, for current-version macro development and execution. Apply the same mature profile to all mature roles; low-level exclusions must reflect actual unlocks only. Prefer targeted validation of new or changed actions over repeating stable full batches.

- Read `docs/PROJECT-CONTEXT.md` for user authorization and the low-cost game-resource experiment model. Do not add repeated project-level approvals for already-authorized game actions or treat virtual resources as real money. Game strategy belongs to the visit plan/local role configuration; system permissions and real payment remain separate. This does not override platform-enforced review, account scope, pause state or the no-payment boundary.

- Use 三班 (America/Vancouver local21:00/03:00/09:00; UTC game day tracked separately) terminology and classify tasks by shift/day/week/four-week/event. Read `docs/V2-OPERATIONS.md` for pilot and fresh V2 worker boundaries. At the next user discussion, raise `docs/RESOURCE-TASK-PRIORITIES.md`; that discussion must not reduce daily coverage.

- The user cancelled the Orchestrator role on 2026-10-18 and grants this leader direct WOS control. No external slot or notification is required. Retain the actual single-executor lock and local lease. Capture suite/action versions and hashes in reports; prefer useful targeted tests over repeating unchanged stable flows.

科研与建筑升级属于独立升级能力，不属于日常；保留action，但所有三班清单排除research/construction，不因空闲队列、红点或补日常而启动升级。训练和治疗仍在日常范围。用户明确于2026-10-18。

## 沙盒试验背景（2026-10-21）

用户将本项目内的游戏运行视作沙盒试验：游戏状态、虚拟资源、奖励和操作失误均属于可接受的试验成本，不作为需要保护的现实资产。优先跑通流程、扩大覆盖、采集并积累可复用数据；不要为虚拟资源保值增加审批、保守跳过或多余确认。这是项目的成本判断，不是对游戏环境或外部系统“绝无风险”的技术保证。

四个既有角色的游戏内操作已统一授权，包括主号。开发者可根据现场情况导航、领取、派遣、使用游戏资源、处理弹窗、恢复页面、正常重启游戏、采样新流程、修订宏并定向复测；不再要求失败必须留到下一班，也不把模型限制为只能观察。具体次数、目标与频率是可调整的游戏策略，不是审批门槛。优先自动宏，模型介入用于提高覆盖和生成下一版宏，分别记录两者的操作与结果。

此前“只记偏差不补做”“失败同轮不能复测”“未知页面只能等待用户处理”及额外的游戏行为禁令不再作为当前开发限制。历史运行记录、旧版本行为和实际代码保护条件仍如实保留；改变执行器行为需正常修改、版本化及验证，不伪称只改文档就已生效。

此背景不改变系统权限、平台强制审核、真实支付、外部通信授权或私有数据管理。真实支付仍由用户本人完成。唯一执行锁用于避免并发抢窗口；身份、尺寸和页面核验用于定位与恢复，不是虚拟资产保护审批。平台拒绝时不绕过；环境可用后可按实际状态恢复开发。
