# NewGAN Manager（ByHzH 版）

![Windows](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/Windows/badge.svg)
![Linux](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/Linux/badge.svg)
![MacOS](https://github.com/huangzhanhao/NewGAN-Manager-ByHzH/workflows/MacOS/badge.svg)

**当前版本：v1.4.4** ｜ Fork 自 [Maradonna90/NewGAN-Manager](https://github.com/Maradonna90/NewGAN-Manager)（上游已停止维护）

给 Football Manager 的 NewGAN / 随机人批量匹配头像（facepack）的桌面工具：
读取 FM 导出的 RTF 球员名单 → 按「国籍 + 种族代码」映射到头像包中的图片 → 生成 FM 能识别的 `config.xml`。

图形界面基于 [BeeWare / Toga](https://beeware.org/)，支持 Windows、macOS、Linux。

---

## 本分支相对原版的改动

| 功能 | 说明 |
| :--- | :--- |
| **多 Profile 管理** | 为不同头像包 / 不同存档各建一套 Profile（头像包目录 + RTF + 映射快照）。切换 Profile 时自动把当前 `config.xml` 备份回 `.user/<Profile>.xml`，再把目标 Profile 的快照写回头像包目录 |
| **中文数据库支持** | 可识别中文表头、中文国籍的 RTF 导出；国籍中文名会先翻译回英文三字码（`.config/nat_translation.json`）再查种族映射，因此**无需把 FM 语言切成英文** |
| **只处理随机人** | `only for NewGAN players` 开关：依据 RTF 最后一列（`Yes/No`、`是/否`）过滤，只给随机人换脸；被过滤掉的球员不会被写入 `config.xml` |
| **单个球员换脸** | 底部 Viewer 区：输入 UID 预览当前使用的头像与球员信息（国籍、发色、种族码、肤色、俱乐部、年龄、身高、体重），再选一张图片只替换这一个人 |
| **config.xml 自动备份** | 每次写入前生成 `config备份_YYYYMMDD-HHMMSS.xml`，每个头像包目录最多保留最近 10 份 |
| **应用内日志面板** | `Log` 标签：按级别筛选、`only show this level` 只看某一级、一键打开日志文件、清空显示。日志文件 10 MB × 3 份滚动 |
| **进度与取消** | `Replace Faces` 带进度条与状态文字，解析/映射/写文件放到线程池执行，避免界面卡死；执行中可点 `Cancel` |
| **缺失目录提示创建** | 头像包缺少某个种族子目录时逐个询问是否创建，不必手工补目录 |
| **图片池优先级** | 选图顺序：国籍同名目录 → 种族目录 → 两者都不存在时使用头像包内全部目录 |
| **中文注释 / 双语日志** | 核心代码补充中文注释；日志消息统一为英文，便于跨语言排查 |

---

## 环境要求

- **普通用户**：直接下载 Releases 中的安装包，无需安装 Python。
- **源码运行**：Python 3.11 + `toga` 0.5.2（依赖见 `requirements.txt`；Windows 精简开发依赖见 `requirements-windows-dev.txt`）。

---

## 安装

### Windows
1. 下载并解压 `NewGAN-Manager-*-Windows.zip`，运行其中的 `.msi` 完成安装。
2. 把仓库里的 `views/`、`filters/` 两个文件夹复制到 FM 用户目录：
   `文档\Sports Interactive\Football Manager 20XX\`
3. 首次运行建议**以管理员身份**运行（头像包常放在受保护路径下，写 `config.xml` 需要权限）。

### Linux
1. 解压 `.zip`，赋予可执行权限：`sudo chmod +x *.AppImage`。
2. 把 `views/`、`filters/` 复制到 FM 用户目录。
3. 视权限情况用 `sudo` 运行。

### macOS
1. 双击 `NewGAN-Manager-vX.X.X.dmg` 挂载，把 App 拖入 `Applications`。
2. 把 `views/`、`filters/` 复制到 `~/Library/Application Support/Sports Interactive/Football Manager 20XX/`。
3. 若无法启动，用 Rosetta 打开。

---

## 使用流程

### 1. 在 FM 中导出 RTF
安装 `views/` 后，在 FM 里使用 **`SCRIPT FACES player search` / `squad` / `shortlist` / `staff`** 视图（配合 `filters/` 里的 `is newgen search filter` 只看随机人），把列表**另存为 RTF** 文件。

导出的 RTF 至少需要以下列，顺序固定：

```
| UID       | Nat  | 2nd Nat | Name             | 头发长度 | 发色 | 种族码 |
| 2000472008| ESP  | USA     | Pepe Sáenz       | 1        | 12   | 1      |
```

本分支额外支持：
- **中文表头 / 中文国籍**（如 `| 编号 | 国籍/地区籍 | 第二国籍/地区籍 | 姓名 | ... |`，国籍写「美国」这类中文名）；
- **14 列扩展格式**，多出的列为：肤色码、Face、俱乐部、年龄、身高、体重、`是否为随机人`——只有带最后一列时，`only for NewGAN players` 开关才能生效过滤。

> UID 默认按随机人处理并加上 `r-` 前缀；当 `是否为随机人 = No / 否` 时改回纯数字 UID。

### 2. 在主界面填 4 项
| 项目 | 说明 |
| :--- | :--- |
| **Create / Select Profile** | 新建并选择一个 Profile；`No Profile` 为占位状态，不能删除 |
| **Images Directory** | 头像包**根目录**（其下是 `African`、`Asian`……等种族子目录） |
| **RTF File** | 上一步导出的 RTF 文件 |
| **Mode** | `Preserve` 保留已换过的脸，只补新的；`Overwrite` 对名单内球员全部重抽，名单外的保留；`Generate` 无视现有 `config.xml`，从零生成 |

### 3. 选择开关后执行
- `Allow Duplicates`：允许不同球员复用同一张头像（关闭时 Preserve 模式会先剔除 `config.xml` 已用图片）。
- `only for NewGAN players`：只处理随机人。
- `Save backup of config.xml`：写入前备份原文件。

点击 **Replace Faces**，等待进度到 100% 并弹出 `Finished! :)`。

### 4. 回 FM 生效
`偏好设置 → 界面` 中**取消再勾选皮肤、重新加载皮肤缓存**（Reload skin cache），必要时清理缓存后重启 FM。

### 5. 个别球员不满意？
在 Viewer 区输入该球员 UID 回车 → 查看当前头像 → `Browse` 选一张新图（路径需形如 `...\<种族目录>\<图片名>.png`）→ **Replace it**，仅改写这一条映射。

---

## 头像包目录与种族

图片目录根下需要存在以下 14 个种族子目录（**名称必须完全一致，含 `Seasian` 这一上游历史拼写与带空格的目录名**）：

| 目录名 | 含义 | 目录名 | 含义 |
| :--- | :--- | :--- | :--- |
| `African` | 撒哈拉以南非洲 | `MESA` | 中东与南亚 |
| `Asian` | 东亚 | `SAMed` | 南大西洋与地中海 |
| `Caucasian` | 东欧 / 斯拉夫 | `Scandinavian` | 北欧 |
| `Central European` | 中欧、西欧 | `Seasian` | 东南亚 |
| `EECA` | 东欧与中亚 | `South American` | 拉美混血 |
| `Italmed` | 意大利与地中海 | `SpanMed` | 伊比利亚半岛 |
| `MENA` | 中东与北非 | `YugoGreek` | 巴尔干与希腊 |

- 还可以放**国籍同名目录**（如 `ARG/`、`CHN/`），选图时优先于种族目录。
- FM 的种族码（0–10）如何参与修正选池，见 [种族特征分类说明.md](src/newganmanager/resources/种族特征分类说明.md) 与 [种族代码示例.xlsx](src/newganmanager/resources/FM%20NewGAN种族代码示例.xlsx)；映射规则的实现见 [FaceMapper.correct_ethnic](src/newganmanager/core/FaceMapper.py)。
- 国籍 → 种族的对照表在 `.config/eth_cfg.json`，可自行增改。

---

## 应用数据与配置文件

程序数据都在应用目录（源码运行时为 `src/newganmanager/`）下：

```
.config/
  eth_cfg.json          国籍（英文三字码）→ 种族目录 对照表
  nat_translation.json  中文国籍 → 英文三字码 对照表（解析中文 RTF 用）
  config_template       config.xml 的固定头尾模板，[players] 为占位符
.user/
  cfg.json              Profile 列表与激活状态（仅一个为 true）
  default_cfg.json      首次运行时复制为 cfg.json
  <Profile>.json        单个 Profile 的 img_dir / rtf 等设置
  <Profile>.xml         单个 Profile 对应 config.xml 的快照（切换 Profile 时交换）
newgan.log              运行日志（10 MB × 3 滚动）
```

---

## 从源码运行与打包

```bash
# 安装依赖（Windows 开发环境可用 requirements-windows-dev.txt）
pip install -r requirements.txt

# 运行：在 src/ 目录下
cd src && python -m newganmanager

# 或用 briefcase 开发者模式（在项目根目录）
python -m briefcase dev

# 打包
briefcase build
briefcase package        # 产物在 dist/
```

VSCode 用户可直接使用已配置好的任务与调试（运行 / 测试 / 构建 / flake8），说明见 [.vscode/README.md](.vscode/README.md)。

```bash
# 测试（当前为接口占位，断言待补）
python -m unittest discover -s src/tests -p "test*.py"
```

架构、类与方法清单、替换流程与 UML 见 [src/newganmanager/README.md](src/newganmanager/README.md)。

---

## 故障排查

出问题时请先附上日志文件 `newgan.log` 再提 issue：
- 最快的定位方式是在 `Log` 标签把级别选到 `DEBUG` 复现一次，点 **Open Log File** 直接打开日志。
- 源码运行时日志在 `src/newganmanager/newgan.log`；Windows 打包版在应用安装目录（通常 `%localappdata%\Programs\NewGAN-Manager\`）下。

| 现象 | 原因与处理 |
| :--- | :--- |
| `The RTF file is invalid!` | RTF 表头/列顺序不符合要求，或用其他分隔符导出了。用本仓库 `views/` 视图重新导出；日志里会写明识别到的语言 |
| `The RTF file doesn't exist!` | 文件被移动或改名，重新在 `RTF File` 中选择 |
| `Folder 'X' is missing...` | 头像包缺少种族目录，选择"是"让程序创建，或确认选的是头像包**根目录** |
| 大量 `primary nationality ... is None - skipping` | `.config/eth_cfg.json` 缺少该国籍码（例如 FM 用了非英文三字码），补条目即可 |
| 中文 RTF 中国籍未翻译 | 在 `.config/nat_translation.json` 的对应语言节点里补「中文名 → 三字码」 |
| 名单里一个人都没换 | 勾了 `only for NewGAN players` 但 RTF 没有「是否为随机人」列，或该列全为 `No`；关掉开关或改用带 14 列的视图导出 |
| 写 `config.xml` 失败 / 权限错误 | 以管理员（或 `sudo`）运行，或把头像包移到当前用户可写目录 |
| FM 里头像没变 | 未重新加载皮肤缓存；或 FM 的图形缓存目录里存在旧的 `config.xml` 副本 |

---

## 已知问题与待办

- `Profile` 标签页目前是空占位（Profile 管理仍在 `Main` 标签内），见分支 `TODO：ProfileTab`。
- `.github/workflows/*` 的测试步骤仍指向上游旧模块路径（`src/test_app.py`、`src/test_mapper.py`），重构后已失效，需更新为 `src/tests/`，因此 CI 徽章只作参考。
- `check_for_update()` 指向的是上游仓库，暂未接入本分支版本源，UI 未调用。
- 头像包目录含中文/特殊字符路径时，个别系统上图片预览可能加载失败。
- `src/tests/` 用例多为 TODO 占位，断言待补。

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
