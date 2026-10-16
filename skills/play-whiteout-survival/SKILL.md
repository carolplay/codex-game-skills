---
name: play-whiteout-survival
description: 通过 macOS 本地 Whiteout Survival 应用执行角色日常、领取收益和维护队列，或协调既有多角色任务；将游戏流程、账号目标与设备调度分开处理。
---

# Whiteout Survival：三层工作约定

先从调用线程读取目标王国/角色/ID、等级、账号目标、资源预算、时限、日志位置和既有设备/调度授权。个人信息与授权保留在调用方本地，公开技能不内置账号、时区、排程或机器路径。未明确字段仅在影响下一步时询问；已有用户授权不重复请求。

按问题只读所需层，不每次加载全部历史：

1. **游戏日常**：[references/game-dailies.md](references/game-dailies.md)——任务顺序、领奖、灯塔、队列与完成核验。具体收益入口读 [references/free-rewards.md](references/free-rewards.md)，可选玩法读 [references/optional-dailies.md](references/optional-dailies.md)，界面细节读 [references/ui-workflows.md](references/ui-workflows.md)。
2. **账号目标与优先级**：[references/account-goals.md](references/account-goals.md)——主号、小号、试验号如何分配资源与试验预算，避免把谨慎误作拒绝执行已授权任务。
3. **macOS、iCloud与调度**：[references/macos-orchestration.md](references/macos-orchestration.md)——原生输入、单实例串行、主协调调配、重连、设备暂停与审批错误分类。

等级/任务频率和用量研究按需读 [references/progression-and-coordination.md](references/progression-and-coordination.md)。

## 最小共同约定

- 先核验目标身份，仅操作指定角色。共享同一iCloud/游戏实例时执行权唯一。
- 只通过当前环境支持的原生UI工具操作；不因技能存在而推断可使用游戏后台协议或内存控制。
- 遵守调用方原deadline，查询、等待恢复、记录均计时；未指定单次时限默认30分钟，至少提前2分钟收尾，多角色按调用方预留时间。
- 不现金购买、不野外攻击玩家、不发送聊天。授权的竞技场和NPC集结按账号策略执行；资源预算依用户配置，不把普通消耗都升级成审批事项。
- 记录完成证据、未完成项、队列、任务与设备错误分类、耗时及实际可读用量。未知token/credit不估算为精确成本。
