# 宏发布包与执行入口

WOS业务文件由本skill维护；CrossMacro提供通用执行器。身份、预算、机器路径、截图、完整录制与运行记录留在Git忽略的local-data。

当前包0.8.1，执行器最低0.2.2；45份动作文件（42个日常业务动作、2个独立升级动作与1个档案工具）。动作版本不代表验收通过，范围以catalog、visit-plan与本地证据为准。主号与成熟角色使用同一完整当前清单，低等级按实际解锁；不再保留主号精简旧版。

- catalog.json注册动作路径、action_id/action_version、内容SHA256、周期、验证范围和未实现/部分覆盖项目。
- actions/维护唯一业务步骤；assets/只含可复用小图标，完整账号截图不公开。
- macros/shift-{1,2,3}.json固定顺序与动作版本/哈希；每项须纳入或声明排除原因，每日任务领奖置尾。
- scripts/macro_package.py离线校验包、哈希与各profile；默认不进行游戏输入。
- scripts/run_visit.py一次调用完整组合并冻结内存快照，显式--execute才运行；--tasks是开发定向入口，报告标为targeted-development，不冒充完整班次。

```sh
python3 scripts/macro_package.py
python3 scripts/run_visit.py \
  --executor-dir /path/to/CrossMacro/tools/macos-window \
  --manifest macros/shift-3.json --profile mature-test \
  --config /private/role-config.json --log-root /private/runs \
  --lock-file /private/visit.lock --guard-script /private/guard.py
```

追加--execute才输入。Orchestrator已取消，leader直接掌握窗口；仍须真实flock和本地lease完成准备→宏→准备/释放的串行交接，不能伪造空闲。后端保持一个，自动推进本地OCR/图像条件，不需agent操作CrossMacro编辑器。业务偏差预定义有界退出；全局身份/权限/锁屏/尺寸及未知出口失败停批。

执行器0.2.0支持局部OCR、严格数字读回、显式低置信数字阈值、领取后数字增长与纯观察重读、多个队列计时区域、校准红点、图标模板、有限方向键批量导航、声明式提前完成和跳过依赖。图像匹配使用NumPy与Pillow，在本地完成；模板由私有config的image_templates把语义名称映射到本skill assets绝对路径。缺模板或页面不明时失败，不猜点击坐标。旧的单一OCR目标默认仍必须唯一；只有动作明确声明select=top-left才从多个合法候选中选最上方。

发布动作修改时升对应action版本、重算catalog哈希、更新各组合pin并升组合及包版本。报告保留包/组合/action版本与哈希和执行器版本；不回写旧报告。开发按一个角色一次→修订→下个角色迭代，固定批次内不热改，不由agent补做。

编辑器导出的旧逐步.macro只代表当时快照，不自动获得新动作或退出逻辑。正式编辑器/调度可用一个Shell动作调用本入口。锁屏下独立CUA可信关联仍未验收，包存在和定时启用不表示长期锁屏可靠。

科研research和建筑construction保留在catalog与actions中，分类为progression/upgrade。三份shift清单的所有profile均明确排除，不计入日常分母；只按另行指定的升级目标调用。

0.2.2增加page_text_only：显式指定局部截图范围时，条件仅检查该范围的OCR；旧page_text_regions仍为整屏补充观察。用于NPC菜单与背景文字隔离，保留局部玩家控件排除，不因背景集结文字拒绝正确NPC。
