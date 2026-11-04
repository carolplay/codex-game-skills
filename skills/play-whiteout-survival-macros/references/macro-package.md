# 宏发布包与执行入口

当前版本及执行器最低要求读取`catalog.json`；动作步骤读取`actions/`，profile与顺序读取`macros/shift-N.json`。各批实际版本、哈希及源码快照以summary为准，发布不代表现场验收。旧部署记录见[清理前快照](../../../docs/archive/wos-instructions-2026-11-03/skills/play-whiteout-survival-macros/references/macro-package.md)，仅排查对应版本时加载。

## 校验与执行

以下从本skill目录运行。角色配置、依赖与机器路径由本地调用方提供。

```sh
python3 scripts/macro_package.py
python3 scripts/run_visit.py \
  --executor-dir /path/to/CrossMacro/tools/macos-window \
  --manifest macros/shift-3.json --profile mature-test \
  --config /private/role-config.json --log-root /private/runs \
  --lock-file /private/visit.lock --guard-script /private/guard.py
```

不带`--execute`只校验；添加该参数才输入。`--tasks TASK...`是定向开发子集，不能冒充完整班次。`main`、`mature-test`及`under30-test`是否适用按本地绑定和实际解锁判断，不能由profile名字推断主号只用旧版或免测。

`run_visit.py`执行所选manifest，不自动实现每个日内多次目标。现有本地交错组合可在核心小段之间推进巨兽、免费招募及仓库冷却恢复；组合自身须版本化、冻结源码与配置，记录完整顺序和额外尝试。角色切换及准备交接按[V2-OPERATIONS](../../../docs/V2-OPERATIONS.md)，不需要操作CrossMacro编辑器。

修订action时递增其版本，重算catalog内容哈希，并同步所有相关manifest的包／组合版本和pin。先做包级校验、执行器schema及相关正负样本检查，再用自然适用角色定向验证；不重复已完成的日内唯一收益来刷通过。

## 本地部署与模板

私有config提供目标应用路径、身份、OCR二进制、运行目录、guard和已验证尺寸档；不可把完整账号截图或余额放入公共assets。`image_templates`把action中的语义别名映射到本地资产绝对路径；支持的模板数量、匹配范围及阈值以当前执行器与对应action为准，不沿用旧发布说明中的常量。

已用到的非显然部署点：

| 别名 | 用途与注意事项 |
|---|---|
| `intel-bulk-locked` | 低等级情报站虽显示全部执行文字，仍可能带锁；绑定锁图案并按action分流，不能仅凭文字走批量。 |
| `arena-expedition-claimed-chest` | 新竞技场已开箱仍显示5/5，区别未开箱；领取、零剩余与图案分别核验，当前阈值只读action。 |
| `treasure-ready-v3`／`treasure-complete` | 寻宝可派和已完成图案是不同状态；绑定当前配色变体，检查实际整图搜索范围，不以裁区匹配代替完整扫描验收。 |
| `island-tree-guide`／`island-life-bubble` | 指引和普通产出气泡分开绑定；入口、点击与库存增长分开验收。 |
| `stamina-zero` | 可选的本机空体力字形模板；缺绑定不假定体力为零或足够，保留本地数字读回。 |

其他模板按选中action实际引用部署；缺失模板是配置缺口，不是已领取或未解锁。旧别名仍被历史快照使用时保留兼容，不能在运行中悄悄替换其含义。

尺寸选择只接受已经现场核验的本地固定档位；保存原始图、实际像素、映射与锚点证据，批次中不热换。窗口和系统故障恢复按运行规范处理，部署文档不授予新权限。
