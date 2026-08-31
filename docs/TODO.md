# NewGAN Manager 待办任务清单

> 基于 2026-08-31 全项目代码审查（master 分支，Toga/BeeWare 版）整理。
> 当前工作分支：`fix/code-review-batch1`（提交 e79a64c，尚未推送/合并 master）。
> 每项任务标注了涉及文件、问题描述、建议做法与优先级，方便下次直接开工。

---

## 一、已完成（本次 fix/code-review-batch1 分支，供回顾）

| # | 任务 | 实现方式 |
| :--- | :--- | :--- |
| 1 | 清理非 master 分支 | 删除本地/远程 `TODO：ProfileTab`、远程 `Original-version-1.4.0` |
| 2 | 修复 Generate 模式双重映射 Bug | `FaceMapper._process_generate_mode` 改为每球员只调用一次 `_build_player_mapping`（原写法在列表推导的条件与取值处各调用一次，关闭 Allow Duplicates 时图片池被过度消耗） |
| 3 | 修复 Cancel 无法真正中断替换任务 | 新增 `threading.Event` 取消标志：`MainTab._cancel_replace_faces` → `ReplaceFacesService.request_cancel()` → `FaceMapper.generate_mapping(cancel_event=...)` 映射循环逐球员检查；取消后不再写 config.xml |
| 4 | 用户数据迁移到 paths.data | `.user/` 运行时数据与 `newgan.log` 写入 Toga `paths.data`（各平台标准用户数据目录）；旧版应用目录下的 `.user/` 首次启动自动迁移；`.config/` 只读资源留在应用目录。涉及 `app.py`、`ProfileManager.py`（新增 `data_dir` 参数与 `user_path()`）、`NewGanLogManager`、`app_log_tab.py` |
| 5 | 删除误提交的用户 RTF 文件 | 删除 `src/newganmanager/user_rtf/` 下 27 个 RTF，`.gitignore` 增加 `user_rtf/` 规则 |
| 6 | 文档整理 | 删除《Toga替换评估方案.md》《打包与Web化方案.md》；`src/newganmanager/README.md` → `docs/ARCHITECTURE.md`；种族说明移入 `docs/`；README 全部链接同步更新 |
| 7 | 拆分 app_main_tab | 656 行拆为三部分：`app_main_tab.py`（主 Tab UI + Profile 管理）、`app_replace_service.py`（替换流程编排 + 取消）、`app_viewer.py`（球员预览 / 单人换脸） |
| 8 | 重建 CI + 更新 pyproject | 删除 `hello-world.yml`；三平台工作流改为 test + build 两个 job、测试路径修正为 `src/tests/`、actions 升级到 v4/v5；`pyproject.toml` 补充 PEP 621 `[project]` 元数据与 `[build-system]` |
| 9 | Profile 管理重写（多组） | 一个 Profile 支持多个头像包目录（组 = img_dir）；`ConfigManager` 并入 `ProfileManager`（删除 `core/ConfigManager.py`）；删除 `migrate_config`；`swap_xml` 改为多目录快照保存/恢复；`<name>.json` 新结构 `{"cur_group", "groups": {<img_dir>: {"rtf"}}}`；组快照存 `.user/<profile>/<sanitized>.xml` |
| 10 | 启用 Profile 标签页 | 新增 `app_profile_tab.py`：组列表展示、删除组、切换当前组；Main 标签选择新头像包目录时自动建组；替换流程仅对当前组执行 |

验证情况：`py -m compileall` 通过；ProfileManager 多组流程（建档 / 自动建组 / 双组 / 切换快照交换 / 删组 / 删档）自检脚本全部通过。
注意：本地环境未安装 toga，UI 层改动仅做了语法级验证，**建议真机运行一次**（首次启动、选目录自动建组、多组切换、替换流程、Profile 标签页删组）。

---

## 二、待办任务（按优先级排序）

### P0 - 合并前必须确认

#### 1. 真机运行验证本次改动
- **范围**：`pip install toga requests dhooks` 后运行 `cd src && python -m newganmanager`
- **验证点**：
  - 首次启动后 `.user/` 与 `newgan.log` 是否生成在用户数据目录（Windows 为 `%LOCALAPPDATA%\NewGAN Manager\` 一类的路径）而非 `src/newganmanager/` 下；
  - 旧数据迁移：手动在 `src/newganmanager/.user/` 放一份 `cfg.json`，启动后应被复制到用户数据目录；
  - Replace Faces 全流程正常、进度条正常；
  - 替换进行中点 Cancel，状态文字变 "Cancelled"，头像包目录的 `config.xml` 未被修改；
  - Viewer 区 UID 预览、单人 Replace it 正常；
  - 切换 Profile 后各输入框刷新正常。
- **原因**：本地无 toga 环境，`app.py` / `app_main_tab.py` / `app_viewer.py` / `app_replace_service.py` 的运行时行为未验证。

### P1 - 高优先级

#### 2. 补核心模块单元测试
- **现状**：`src/tests/test_app.py` 241 行里断言多为 TODO 占位（`self.assertTrue(True)` 之类），CI 的 test job 实际形同虚设。
- **建议用例**（测试数据在 `src/tests/testing_data/` 已齐全）：
  - `RtfParser`：英文/中文 RTF 的 `check_rtf_valid`；`parse_rtf` 对 7 列基础格式与 14 列扩展格式的解析；`only for NewGAN` 过滤（`是/否`、`Yes/No`）；UID `r-` 前缀逻辑；非法 UID / 越界种族码跳过；中文国籍翻译（`nat_translation.json`）。
  - `FaceMapper.correct_ethnic`：种族码 0–10 全分支的期望输出（纯函数，最容易测）。
  - `FaceMapper.generate_mapping`：Preserve / Overwrite / Generate 三模式；Allow Duplicates 开/关（重点回归：Generate + 不允许重复时，映射数量应等于成功球员数、图片不重复）；`cancel_event` 置位后返回 None。
  - `XmlParser`：`parse_xml` / `get_imgpath_from_uid` / `write_xml`（含备份生成与 10 份上限清理）/ `single_replacement_in_xml`。
  - `ProfileManager`：create / delete / load / swap_xml（testing_data 里有 `.user` 样例）。
- **注意**：跑完测试后 `git restore -- src/tests/testing_data`（见任务 8）。

#### 3. Profile 切换与替换任务的竞态防护
- **问题**：`ProfileManager.swap_xml` 会覆写头像包里的 `config.xml`；若替换任务正在线程池中执行，两者会互相覆盖，可能产生半成品配置。
- **建议**：替换任务运行期间禁用 Profile 下拉框与 Delete 按钮（`MainTab._replace_faces` 开始时禁用、`_cleanup_after_replace` 恢复），改动量最小。

#### 4. ConfigManager.save_config 原子写入
- **问题**：直接 `open(path, "w")` 覆盖写 JSON，进程中途崩溃（或断电）会留下截断损坏的配置文件，下次启动 `load_config` 抛 `JSONDecodeError` 且无恢复手段。
- **建议**：写临时文件 + `os.replace(path_tmp, path)`；`load_config` 捕获 `json.JSONDecodeError` 时尝试备份损坏文件并回退默认配置。
- **文件**：`src/newganmanager/core/ConfigManager.py`

### P2 - 中优先级

#### 5. 死代码清理
- `app.py` 的 `check_for_update()`：指向上游仓库（Maradonna90），UI 从未调用。要么删除（连同 `requests` 依赖），要么改为指向本仓库 `version` 文件并在启动时调用。
- `FaceMapper.pick_image()`：标注"兼容旧版"，仓库内已无调用方，可删。
- `core/Reporter.py`：20 行，依赖 `dhooks`（Discord webhook），无调用方。删除后可从 `pyproject.toml` 与 CI 依赖里去掉 `dhooks`。
- `app.py` 顶部注释掉的 import 与 Discord webhook URL 常量、`NewGanLogManager` 中 `app.py` 已不用的 `shutil` import 等，一并清理。
- **注意**：删 `dhooks` 前先全局搜索确认无其他引用；同步更新 `pyproject.toml`、三个 CI workflow 的 `pip install` 行、README。

#### 6. ~~migrate_config 相对路径问题~~（已完成：函数随 Profile 重写一并删除，见上表 #9）

#### 7. 路径处理统一 + 代码规范
- **问题**：大量 `"/"` 字符串拼接路径（如 `deact_img_dir+"config.xml"`、`path_name + "/"`），Windows 下产生混合分隔符；`toga.Image("resources/favicon-400×400.png")` 依赖 CWD 相对路径，双击启动 / 其他目录启动时可能加载失败。
- **建议**：
  - 全项目改用 `pathlib.Path` 或 `os.path.join`；
  - 图片等资源改为基于 `__file__` 或 `app.paths.app` 的绝对路径定位；
  - `FaceMapper.__init__` 中 `for dir in eth_dirs` 遮蔽内置名 `dir`，改名为 `eth_dir`；
  - `app_log_tab.py` / `NewGanLogManager.py` 中的 `asyncio.get_event_loop()`（3.10+ 弃用警告）改 `asyncio.get_running_loop()`（需确认只在事件循环内调用）。
- **规范**：pyproject 增加 `[tool.ruff]` 配置（line-length 120、基础规则集），修一遍存量告警，CI 的 test job 中加 `ruff check src/`。

#### 8. 测试基架缺陷：tearDown 误删跟踪文件
- **问题**：`src/tests/test_app.py` 的 tearDown 会删除 `src/tests/testing_data/` 下被 git 跟踪的固定文件（`.user/No Profile.json`、`.user/cfg.json`、`config.xml` 等），每次本地跑完测试工作区就变脏，需要手动 `git restore`（本次开发中已踩坑两次）。
- **建议**：setUp 阶段把 testing_data 复制到临时目录（`tempfile.TemporaryDirectory`），测试全部在副本上进行，tearDown 只清理临时目录。

#### 9. UI 预览的文件 I/O 阻塞主线程
- **问题**：`app_viewer.py` 的 `_on_preview_uid_confirm` 是同步回调，读 config.xml、遍历 mapping_data、加载图片都在 UI 线程执行，名单大时点回车会卡界面。
- **建议**：改为 async 回调，文件读取与 `toga.Image` 构造放 `run_in_executor`；顺带把 mapping/rtf 数据的线性查找改为 dict 索引（UID → 记录）。

#### 10. ~~Profile 标签页空占位~~（已完成：ProfileTab 已启用，组管理已迁入，见上表 #10）

### P3 - 低优先级 / 增强

#### 11. 面向用户的更新检查
- 删除或改造 `check_for_update()`（见任务 5）：若保留，指向本仓库 `version` 文件，UI 菜单加 "Check for Update" 命令，弹窗提示并打开 Releases 页。

#### 12. 异常处理降噪
- `app_main_tab.py` 与 `ProfileManager.py` 中多处 `except Exception: pass` / `except OSError: pass`（如 `_action_select_folder_dialog`、`create_profile`），错误被吞掉后用户只看到"没反应"。
- 建议：至少 `logger.error(..., exc_info=True)` + 用户可见的 `throw_error` 弹窗。

#### 13. 头像包中文路径兼容性
- README 已知问题：头像包目录含中文/特殊字符时图片预览可能失败。排查 `toga.Image` 在 WinForms 后端的路径编码处理，必要时给出明确的报错信息。

#### 14. 打包版数据目录回归测试
- Briefcase 打包后 `paths.data` / `paths.app` 的实际值与源码运行不同（msi 安装到 Program Files 时应用目录只读）。任务 1 验证源码运行后，还需用 `briefcase package` 产物在干净机器上过一遍首启流程（默认配置复制、日志创建、旧数据迁移）。

---

## 三、任务状态记录

| 日期 | 变更 |
| :--- | :--- |
| 2026-08-31 | 基于代码审查建立本清单；第一轮修复（8 项）完成于 `fix/code-review-batch1`（e79a64c），待真机验证后合并 master |
| 2026-08-31 | Profile 管理重写（多组）+ 启用 Profile 标签页，见上表 #9 / #10 |

> 完成一项后请更新本表与对应章节状态（移入"已完成"或在标题加 ~~删除线~~），保持本文件为唯一的待办事实来源。
