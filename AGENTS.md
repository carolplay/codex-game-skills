# WOS agent bot workspace

- 现行授权、机器运行时段、账号范围与本地存储总额只维护在[PROJECT-CONTEXT](docs/PROJECT-CONTEXT.md)；三班执行、恢复及报告流程只维护在[V2-OPERATIONS](docs/V2-OPERATIONS.md)。最新用户指示优先；历史快照、旧报告和过去聊天不新增当前限制。
- 公共技能在`skills/`；身份、配置、余额、完整截图、运行证据在Git忽略的`local-data/`，不得提交或复制到公开技能。入口见`local-data/README.md`，当前任务状态读`local-data/orchestration/V2-ITERATION-CURRENT.json`及其指向的检查点。
- WOS生产使用`skills/play-whiteout-survival-macros/`。V1 `play-whiteout-survival/`仅按需提供游戏知识，既有V1排程保持暂停；不从旧角色聊天恢复调度器或权限规则。
- 当前动作、版本、哈希、profile与班次顺序读`catalog.json`、`actions/`和`macros/shift-N.json`；[visit-plan](skills/play-whiteout-survival-macros/references/visit-plan.md)只维护任务backlog与验证范围，不复制旧冻结清单。status使用不知道要不要做／没做／已做／已验证。
- 输入必须持真实`visit.lock`与本地lease，所有角色串行。宏声明入口、出口、业务依赖和有界恢复；每批版本固定，恢复与修订另记证据。具体错误处理按V2-OPERATIONS。
- 截图维护只按`local-data/macro-materials/README.md`和`scripts/retain_macro_screenshots.py`：只留运行模板和明确使用的回归样本，其余画面临时处理；取得真实锁，忙则跳过，不启动游戏或改变排程。
- CrossMacro源码在独立项目目录；运行依赖与机器启动配置不进公共仓库。V3采用通用执行后端＋游戏能力包＋MCP接口，先以WOS验收，后扩展大航海和WoW；方向及迁移条件见[WOS-V3-NATIVE-RUNTIME](docs/WOS-V3-NATIVE-RUNTIME.md)。
