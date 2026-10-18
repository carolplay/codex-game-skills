# WOS agent bot

macOS 原生 Whiteout Survival 的本地宏实验。固定步骤由本地 OCR 和窗口绑定输入执行，agent 只启动与最终检查、记录偏差；不逐步调用模型，不自动补做日常。

## 阅读顺序

先读 [项目背景与操作授权](docs/PROJECT-CONTEXT.md)：虚拟资源容错、游戏策略与系统审批职责、真实支付边界。

1. [V2 架构与当前实现](docs/WOS-AUTOMATION-V2.md)：执行路径、组件职责和实际限制。
2. [V2 任务设计与实施安排](docs/WOS-V2-TASK-DESIGN.md)：宏任务现状、固定起止界面、失败隔离和下一步验收。
3. [V2 执行技能](skills/play-whiteout-survival-macros/SKILL.md)：单次运行规则。
4. [三班任务资料](skills/play-whiteout-survival-macros/references/visit-plan.md)：游戏日常的开发资料，不是当前已覆盖任务清单。

## 仓库边界

- 本仓库保存通用技能、设计与规划脚本；[CrossMacro fork](https://github.com/carolplay/CrossMacro/tree/codex/macos-window-macros/tools/macos-window) 保存本地执行器和宏 JSON。
- `skills/play-whiteout-survival/` 是原样保留的 V1 纯 agent 方案。V2 当前仅处于单次实验阶段，长期定时暂停。
- 私有角色、账号策略、机器配置、截图、音频和运行记录位于 Git 忽略的 `local-data/`，不随代码上传。

当前还不是完整日常机器人。已有固定界面恢复和任务级失败隔离，并有一次连续七宏通过的现场证据；任务覆盖仍不完整，新宏需分别注明分支验证范围。锁屏自动运行也未通过验收。

三班分工与验收见 [V2 operations](docs/V2-OPERATIONS.md)；[wiki贡献准备](docs/wiki-contributions/README.md)保留来源与待核范围；[资源/任务排序](docs/RESOURCE-TASK-PRIORITIES.md)留待下次讨论，不影响全部日常覆盖。
