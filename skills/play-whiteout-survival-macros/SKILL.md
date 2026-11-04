---
name: play-whiteout-survival-macros
description: 开发、执行和迭代Whiteout Survival本地宏，结合模型覆盖检查、现场恢复与录制积累流程数据。
---

# WOS本地宏

项目授权和机器运行时段读[PROJECT-CONTEXT](../../docs/PROJECT-CONTEXT.md)，启动、接续、恢复及报告读[V2-OPERATIONS](../../docs/V2-OPERATIONS.md)。四个既有角色均参与当前版本；不要从V1或历史实验重新引入角色审批、旧时限或失败不能补做的要求。

读取当前本地检查点、角色绑定、catalog与所选manifest，离线校验后持真实唯一锁和lease串行执行。批次固定版本；宏优先，模型可另记恢复、采样和补做，修订后另开批次。每号宏后检查任务栏与面板外日常，按实际领取、冷却、次数和覆盖缺口记账，稳定流程不做无目的重复测试。

按需读取：

- [macro-package](references/macro-package.md)：校验、部署模板、公开执行入口和私有交错组合的区别。
- [visit-plan](references/visit-plan.md)：任务backlog、当前线性清单及分支验证范围。
- [任务契约](../../docs/WOS-V2-TASK-DESIGN.md)：入口／出口、业务依赖、偏差隔离及版本证据。
- [巨兽](references/npc-rally.md)、[猎熊](references/bear-hunt.md)：对应任务的次数闭环和活动规则。
- [录制素材](references/recording-cards.md)：发现新流程时如何保留可复用样本。

具体账号、余额、截图和机器路径留Git忽略的local-data。只有相关失败需要追溯时才读历史迭代，不在正常执行中加载整套旧记录。
