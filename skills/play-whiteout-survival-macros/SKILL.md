---
name: play-whiteout-survival-macros
description: 开发、执行和迭代Whiteout Survival本地宏，结合模型覆盖检查、现场恢复与录制积累流程数据。
---

# WOS V2：本地宏与开发迭代

按[项目背景](../../docs/PROJECT-CONTEXT.md)理解用户的沙盒试验授权：虚拟资源与游戏失误是可接受成本，跑通流程、覆盖日常和积累数据优先。四个既有角色包括主号同等参与；成熟角色用相同适用清单，低等级按实际解锁处理。

读取当前检查点、角色配置、catalog及班次manifest，取得实际唯一执行锁与lease。准备阶段切号并核验身份和窗口。固定流程优先通过本地批处理一次运行，不需要agent逐步操作CrossMacro编辑器。

自动宏以固定入口、出口、依赖及有界恢复组成可组合任务。环境或页面条件不成立时，暂停自动输入并保存证据。权限可用时，开发agent可现场识别、处理弹窗、领取、补做、恢复页面、正常重启游戏，采集新路径并定向复测，不再受仅记录偏差或必须等下一轮限制。不得绕过平台权限拒绝。

每角色宏后检查日常侧栏及visit-plan非侧栏任务。分类缺口为脚本失败、次数不足、未纳入清单、冷却/未解锁、证据不足；必要时直接转入开发采样并提炼宏。稳定流程避免无目的重复，新增/修复动作优先放末段，保留业务依赖及daily最后的安排。

批次保留固定包、组合、action及执行器版本/哈希；修订后另启批次。人工处理、首次失败、修复后宏回放分别记录，不能将人工完成写成旧宏通过。报告实际领奖、冷却、偏差、未执行、覆盖缺口，以及准备/执行/检查耗时；宏内部模型调用不等于整轮token消耗。结束关闭专用backend并释放实际锁和lease。

发布与入口见[macro-package](references/macro-package.md)：先用scripts/macro_package.py离线校验，再由scripts/run_visit.py --manifest ... --profile ... --execute运行。角色身份、机器路径及证据保存在Git忽略的local-data。旧plan_visit.py仅兼容旧离线规划，不代表当前清单。

按需读取[流程卡](references/recording-cards.md)、[visit-plan任务backlog](references/visit-plan.md)和[任务组合设计](../../docs/WOS-V2-TASK-DESIGN.md)。以最新授权为准，不把旧版本中的“本轮不补做/不复测”历史记录重新当作禁令。

声音仅捕获目标游戏进程。真实支付交用户本人；平台系统权限、外部通信授权及私有数据管理仍有效。V1保持暂停，三班America/Vancouver 21:00/03:00/09:00沿用现有排程。科研/建筑是独立升级能力，不计日常；训练/治疗仍属日常。
