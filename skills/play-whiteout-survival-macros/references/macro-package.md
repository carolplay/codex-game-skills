# 宏发布包与执行入口

WOS业务文件在本skill维护，CrossMacro只提供通用执行器和格式/恢复回归样例。公开包不含账号ID、预算、机器路径、截图或运行记录。

- `../catalog.json`：package版本、action路径/版本/内容SHA-256、周期和验证范围。action内旧录制标签保留历史事实，最新证据说明见catalog及visit-plan。
- `../actions/`：16个业务action和1个档案往返工具；迁移不改变原步骤、action版本或内容哈希。
- `../macros/shift-{1,2,3}.json`：组合宏独立版本；顺序固定，action版本及哈希固定。主号、成熟试验号、30级前辅助试验号各有适用清单与明确排除原因。
- `../scripts/macro_package.py`：离线校验所有action和组合。新增action未被组合纳入或明确排除会失败。
- `../scripts/run_visit.py`：一次调用整批执行，记录包、组合、执行器和action身份；默认仅验证，显式`--execute`才输入。

当前package与三份组合均为`0.2.2`，执行器最低`0.1.4`。一班含每日VIP核验，二、三班不重复稳定VIP流程。三班当前主号7项、成熟试验号15项、低等级7项；这是实现覆盖，不是全部日常。银行等未实现任务列在catalog的`not_implemented`中，继续纳入开发。成熟试验号包含失败候选，版本号不表示验收通过。专家仅覆盖已校准营地，训练/招募/捐献的剩余缺口见visit-plan与catalog。

执行示例（路径由本地部署填写，配置包含身份/预算/日账本）：

```sh
python3 scripts/macro_package.py
python3 scripts/run_visit.py \
  --executor-dir /path/to/CrossMacro/tools/macos-window \
  --manifest macros/shift-3.json --profile mature-test \
  --config /private/role-config.json --log-root /private/runs \
  --lock-file /private/visit.lock --guard-script /private/guard.py
```

以上仅校验，追加`--execute`才运行；此前须取得Orchestrator协调时段并设置本地租约，不能把取得flock当成协调完成。运行使用同一个本地后端串行推进，无须agent逐步操作CrossMacro。业务偏差仅按action预定义有界退出，主城确认后才执行下项；全局故障停止本批。报告保留未执行分母和固定版本；检查不由agent补做。

`--tasks task ...`是开发维护定向入口，报告明确标为`targeted-development/adhoc`，不能冒充已发布的班次组合。正式班次使用`--manifest`和对应profile。

发布时：修改action必须升对应版本；更新catalog哈希；更新受影响的各组合pin并升组合版本；包发布升package版本，所有组合声明同一包版本。仅调整顺序或任务纳入也须升组合版本。执行中的内存快照不热改；发布不回写历史运行版本。

CrossMacro编辑器导出的旧逐步`.macro`是当时录制快照，不会自动获得新清单或任务级退出。正式编辑器/调度入口应以一个Shell动作调用上述整批入口；不要重新指向旧录制快照。具体action仍可从本skill的JSON导出作定向录制查看。

锁屏下独立CUA可信线程关联尚未解决；宏迁移和定时存在不代表锁屏已可靠。

0.2.1修订训练action为0.2.0：旧录制样本上限1200误拒绝实际界面数量1318；改为局部OCR核验当前数量1至9999，保留所选兵阶/数量，不操作数量控件。旧图已离线读回1318，现场分支验收另记。

0.2.2增加英雄列表标题/底部的局部page-text OCR（recruit0.1.1，执行器0.1.4），旧失败图离线验证通过；训练0.2.1识别实际出现的“训”部分标签。2827已在0.2.0训练版本通过矛兵和射手，盾兵失败留档；新版本只用于后续账号，不在同班反复试失败项目。
