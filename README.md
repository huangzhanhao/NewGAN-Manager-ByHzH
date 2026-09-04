# NewGAN Manager

> 给 Football Manager 的 NewGAN / 随机人批量匹配头像（facepack）的桌面工具。
> 读取 FM 导出的 RTF 名单 → 按「国籍 + 种族」自动挑一张头像图片 → 生成 FM 能识别的 `config.xml`。

![Windows](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/Windows/badge.svg)
![Linux](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/Linux/badge.svg)
![MacOS](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/MacOS/badge.svg)

**当前版本 v1.4.4** ｜ Fork 自 [Maradonna90/NewGAN-Manager](https://github.com/Maradonna90/NewGAN-Manager)（上游已停止维护）｜ 图形界面基于 [BeeWare / Toga](https://beeware.org/)，支持 Windows、macOS、Linux。

---

## 它解决什么问题

NewGAN（随机人）默认没有头像。手动给成百上千名随机人一张张贴图不现实。这个工具把 FM 导出的球员名单（RTF）和一套按种族分目录的头像包对应起来，**批量**生成 FM 读取的 `config.xml`，让随机人自动"长脸"。

**典型使用一句话：** 导出 RTF → 选头像包目录 → 点 `Replace Faces` → 回 FM 重载皮肤。

---

## 主要功能

- **多 Profile 管理**：不同头像包 / 不同存档各建一套 Profile（记录头像包目录、RTF、映射快照）。切换 Profile 时自动把当前 `config.xml` 备份回 `.user/<Profile>.xml`，再把目标快照写回头像包目录。
- **中文数据库支持**：可识别中文表头、中文国籍的 RTF。国籍中文名会先经 `.config/nat_translation.json` 翻译回英文三字码再查种族映射——**无需把 FM 切成英文**。
- **只处理随机人**：`only for NewGAN players` 开关按 RTF 最后一列（`Yes/No`、`是/否`）过滤，只给随机人换脸，被过滤者不写入 `config.xml`。
- **三种替换模式**：`Preserve` 保留已换过的只补新的；`Overwrite` 对名单内球员全部重抽、名单外保留；`Generate` 无视现有 `config.xml` 从零生成。
- **单个球员微调**：底部 Viewer 区输入 UID → 预览当前头像与球员uid信息→ 选一张图 `Replace it`，只改写这一条映射。
- **自动备份**：每次写入前生成 `config备份_YYYYMMDD-HHMMSS.xml`，每个头像包目录最多保留最近 10 份。
- **进度与取消**：`Replace Faces` 带进度条与状态文字，解析/映射/写文件放线程池执行避免界面卡死，执行中可 `Cancel`。
- **应用内日志面板**：`Log` 标签可按级别筛选、只看某一级、一键打开日志、清空显示；日志文件 10 MB × 3 份滚动。
- **缺失目录提示创建**：头像包缺少某种族子目录时逐个询问是否创建。

---

## 快速开始（普通用户）

1. 到 **Releases** 下载对应平台安装包，安装运行（无需装 Python）。
   - **Windows**：解压 `NewGAN-Manager-*-Windows.zip`，运行其中的 `.msi`。首次建议**以管理员身份**运行（写 `config.xml` 到受保护目录需要权限）。
   - **Linux**：解压 `.zip`，`sudo chmod +x *.AppImage` 后运行，视权限用 `sudo`。
   - **macOS**：双击 `.dmg`，把 App 拖入 `Applications`；若无法启动，用 Rosetta 打开。
2. 把仓库里的 `views/`、`filters/` 两个文件夹复制到 FM 用户目录：
   - Windows：`文档\Sports Interactive\Football Manager 20XX\`
   - macOS：`~/Library/Application Support/Sports Interactive/Football Manager 20XX/`
3. 按下面的[使用流程](#使用流程)操作。

---

## 使用流程

### 1. 在 FM 中导出 RTF
安装 `views/` 后，在 FM 里使用 **`SCRIPT FACES`** 的 `player search` / `squad` / `shortlist` / `staff` 视图（配合 `filters/` 里的 `is newgen search filter` 只看随机人），把列表**另存为 RTF**。

导出的 RTF 至少需要以下列，**顺序固定**：

```
| UID       | Nat  | 2nd Nat | Name        | 头发长度 | 发色 | 种族码 |
| 2000472008| ESP  | USA     | Pepe Sáenz  | 1        | 12   | 1      |
```

本分支额外支持：
- **中文表头 / 中文国籍**（如 `| 编号 | 国籍/地区籍 | … | 姓名 |`，国籍写「美国」这类中文名）；
- **14 列扩展格式**，多出：肤色码、Face、俱乐部、年龄、身高、体重、`是否为随机人`——只有带最后一列时，`only for NewGAN players` 过滤才生效。

> UID 默认按随机人处理并加 `r-` 前缀；当 `是否为随机人 = No / 否` 时改回纯数字 UID。

### 2. 在主界面填 4 项

| 项目 | 说明 |
| :--- | :--- |
| **Create / Select Profile** | 新建并选择一个 Profile；`No Profile` 为占位状态，不能删除 |
| **Images Directory** | 头像包**根目录**（其下是 `African`、`Asian`… 等种族子目录） |
| **RTF File** | 上一步导出的 RTF 文件 |
| **Mode** | `Preserve` / `Overwrite` / `Generate`，见[主要功能](#主要功能) |

### 3. 选开关后执行
- `Allow Duplicates`：允许不同球员复用同一头像（关闭时 Preserve 模式会先剔除 `config.xml` 已用图片）。
- `only for NewGAN players`：只处理随机人。
- `Save backup of config.xml`：写入前备份原文件。

点击 **Replace Faces**，等待进度到 100% 并弹出 `Finished! :)`。

### 4. 回 FM 生效
`偏好设置 → 界面` 中**取消再勾选皮肤、重新加载皮肤缓存**（Reload skin cache），必要时清缓存后重启 FM。

### 5. 个别球员不满意？
Viewer 区输入该球员 UID 回车 → 查看当前头像 → `Browse` 选一张新图（路径需形如 `...\<种族目录>\<图片名>.png`）→ **Replace it**，仅改写这一条映射。

---

## 头像包目录与种族

图片目录根下需要存在以下 14 个种族子目录（**名称必须完全一致**，含 `Seasian` 这一上游历史拼写与带空格的目录名）：

| 目录名 | 含义 | 目录名 | 含义 |
| :--- | :--- | :--- | :--- |
| `African` | 撒哈拉以南非洲 | `MESA` | 中东与南亚 |
| `Asian` | 东亚 | `SAMed` | 南大西洋与地中海 |
| `Caucasian` | 东欧 / 斯拉夫 | `Scandinavian` | 北欧 |
| `Central European` | 中欧、西欧 | `Seasian` | 东南亚 |
| `EECA` | 东欧与中亚 | `South American` | 拉美混血 |
| `Italmed` | 意大利与地中海 | `SpanMed` | 伊比利亚半岛 |
| `MENA` | 中东与北非 | `YugoGreek` | 巴尔干与希腊 |

- 选图池优先级：**国籍同名目录**（如 `ARG/`、`CHN/`）→ 种族目录 → 两者都不存在时使用头像包全部目录。
- FM 种族码（0–10）如何参与修正选池，见 [种族特征分类说明.md](docs/种族特征分类说明.md) 与 [种族代码示例.xlsx](docs/FM%20NewGAN种族代码示例.xlsx)；实现见 [`FaceMapper.correct_ethnic`](src/newganmanager/core/FaceMapper.py)。
- 国籍 → 种族的对照表在 `.config/eth_cfg.json`，可自行增改。

---

## 项目结构

```
NewGAN-Manager-ByHzH/
├── .github/workflows/          # CI：windows/mac/linux 打包 + test.yml 单元测试
├── docs/                       # 设计与说明文档（架构、种族分类说明、示例数据）
├── filters/                    # FM 过滤器（.fmf），复制到 FM 目录，用于只看随机人
├── views/                      # FM 视图（.fmf），导出 RTF 用，复制到 FM 目录
├── src/newganmanager/          # 应用主包
│   ├── __main__.py / app.py    # 入口 + 主应用（窗口、启动、异步、错误处理）
│   ├── app_main_tab.py         # Main 标签：Profile / 目录 / RTF / Mode / 执行
│   ├── app_profile_tab.py      # Profile 标签（当前为占位）
│   ├── app_log_tab.py          # Log 标签：应用内日志面板
│   ├── app_viewer.py           # Viewer 区：单球员预览与换脸
│   ├── .config/                # 只读配置：eth_cfg.json / nat_translation.json / config_template
│   ├── .user/                  # 首启模板：default_cfg.json / No Profile(.json/.xml)
│   ├── core/                   # 业务逻辑层
│   │   ├── ProfileManager.py   #   Profile 增删改查、config.xml 快照交换
│   │   ├── FaceMapper.py       #   国籍 + 种族码 → 头像图片映射
│   │   ├── RtfParser.py        #   解析 FM 导出的 RTF（含中文 / 14 列扩展）
│   │   ├── XmlParser.py        #   依据 config_template 生成 config.xml
│   │   ├── SourceSelection.py  #   图片池优先级与选图
│   │   ├── NewGanLogManager.py #   日志与滚动
│   │   └── Reporter.py         #   外部上报（webhook）
│   ├── services/               # 服务层：player_service / profile_service / replace_service
│   └── resources/              # 图标与图片资源
├── src/tests/                  # 单元测试 + testing_data（RTF / XML / config 样本）
├── pyproject.toml              # briefcase 应用配置与依赖
├── requirements.txt            # 冻结依赖清单
└── README.md / LICENSE / .gitignore
```

> 分层：**GUI（`app*.py`）→ 服务层（`services/`）→ 业务核心（`core/`）**。GUI 只做输入输出与线程调度，映射/解析/写文件逻辑集中在 `core/`，便于单测。
> 运行时生成的 `build/`、`dist/`、`logs/`、`__pycache__/` 以及便携用户数据 `src/newganmanager/data/` 均已在 `.gitignore` 中排除，不纳入仓库。

---

## 开发与打包

```bash
# 1) 建环境（需 Python 3.12.10）并安装依赖
pip install -r requirements.txt        # 或：pip install toga requests dhooks

# 2) 源码运行：在 src/ 目录下以模块方式启动（包用了相对导入，必须 -m）
cd src && python -m newganmanager
#    或用 briefcase 开发者模式（项目根目录）
python -m briefcase dev

# 3) 单元测试（覆盖 FaceMapper / ProfileManager / RtfParser，CI 由 test.yml 运行）
python -m unittest discover -s src/tests -p "test*.py"

# 4) 打包
briefcase build
briefcase package        # 产物在 dist/
```

架构、类与方法清单、替换流程与 UML 见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 应用数据与配置文件

只读资源随程序分发（源码运行时位于 `src/newganmanager/`）；用户运行时数据写入各平台标准用户数据目录（Toga `paths.data`，如 Windows `%LOCALAPPDATA%\<应用名>`、macOS `~/Library/Application Support/<应用名>`、Linux `~/.local/share/<应用名>`）：

```
# 应用目录（随程序分发，只读）
.config/
  eth_cfg.json          国籍（英文三字码）→ 种族目录 对照表
  nat_translation.json  中文国籍 → 英文三字码 对照表（解析中文 RTF 用）
  config_template       config.xml 的固定头尾模板，[players] 为占位符
.user/
  default_cfg.json      首次运行时复制到用户数据目录成为 cfg.json

# 用户数据目录（paths.data）
.user/
  cfg.json              Profile 列表与激活状态（仅一个为 true）
  <Profile>.json        单个 Profile 的 img_dir / rtf 等设置
  <Profile>.xml         单个 Profile 对应 config.xml 的快照（切换 Profile 时交换）
newgan.log              运行日志（10 MB × 3 滚动）
```

从旧版本升级时，应用目录下的旧 `.user/` 数据会自动迁移到用户数据目录。

---

## 故障排查

出问题时请先附上日志 `newgan.log` 再提 issue。最快的定位方式：在 `Log` 标签把级别选到 `DEBUG` 复现一次，点 **Open Log File** 直接打开日志（文件在用户数据目录，如 Windows 的 `%LOCALAPPDATA%\<应用名>\newgan.log`）。

| 现象 | 原因与处理 |
| :--- | :--- |
| `The RTF file is invalid!` | RTF 表头/列顺序不符，或用了其他分隔符导出。用本仓库 `views/` 视图重新导出；日志会写明识别到的语言 |
| `The RTF file doesn't exist!` | 文件被移动或改名，重新在 `RTF File` 中选择 |
| `Folder 'X' is missing...` | 头像包缺该种族目录；选"是"让程序创建，或确认选的是头像包**根目录** |
| 大量 `primary nationality ... is None - skipping` | `.config/eth_cfg.json` 缺该国籍码（如 FM 用了非英文三字码），补条目即可 |
| 中文 RTF 中国籍未翻译 | 在 `.config/nat_translation.json` 对应语言节点补「中文名 → 三字码」 |
| 名单里一个人都没换 | 勾了 `only for NewGAN players` 但 RTF 无「是否为随机人」列，或该列全为 `No`；关掉开关，或改用 14 列视图导出 |
| 写 `config.xml` 失败 / 权限错误 | 以管理员（或 `sudo`）运行，或把头像包移到当前用户可写目录 |
| FM 里头像没变 | 未重新加载皮肤缓存；或 FM 图形缓存目录里存在旧的 `config.xml` 副本 |

---

## 已知问题与待办

- `Profile` 标签页目前是空占位（Profile 管理仍在 `Main` 标签内）。
- `check_for_update()` 指向的是上游仓库，暂未接入本分支版本源，UI 未调用。
- 头像包目录含中文/特殊字符路径时，个别系统上图片预览可能加载失败。
- `src/tests/` 已覆盖 FaceMapper / ProfileManager / RtfParser 三个核心模块，其余模块（XmlParser、SourceSelection、UI）测试待补。
- 替换任务运行期间切换 Profile 存在竞态（`swap_xml` 与写 `config.xml` 互相覆盖），后续版本计划在任务运行时禁用 Profile 切换。

---

## 致谢

上游项目与其贡献者：
**[Maradonna](https://community.sigames.com/profile/50821-maradonna/) (gestalt)** — 发起、编码、图像生成；
**Samaroy** — 协调、图像生成；
**[HRiddick](https://sortitoutsi.net/user/profile/137954)** — 图片清理与后处理；
**[Krysler76](https://community.sigames.com/profile/157461-krysler76/)** — FM 视图制作；
**Ayal**、**[Zealand](https://www.youtube.com/user/FMBaseOfficial)**、**ZeBurgs** — 图像生成。

头像包的种族划分与图片由 NewGAN 项目组产出，本仓库只提供映射工具，不含任何头像图片。

## 许可证

GPL-3.0，详见 [LICENSE](LICENSE)。
