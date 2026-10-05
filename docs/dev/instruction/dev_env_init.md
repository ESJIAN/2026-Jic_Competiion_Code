# 开发环境初始化与故障记录

本文档是本项目**开发环境初始化的唯一入口**，负责：

1. 汇总一键初始化脚本（`scripts/*_env_init.bash`）的使用方式；
2. 记录初始化过程中遇到的**真实故障、根因、修复方式与验收标准**；
3. 规定「开发初始化问题必须留档」的维护约定（见 [§5](#5-维护约定初始化问题必须记录)）。

> **为什么要单独建这份文档**
> 初始化问题几乎都是「机器差异」而非「代码问题」：同一份代码在 A 机器能跑、
> 在 B 机器报 `command not found`，如果不写进仓库，换机器、换人、隔几周之后
> 就要重新踩坑一遍。本文档 + 脚本入库，就是为了让环境问题从「口头知识」
> 变成「仓库资产」。

---

## 1. 环境基线

| 项目 | 版本/说明 |
| --- | --- |
| 目标硬件 | 地瓜机器人 RDK X5 8GB |
| 操作系统 | Ubuntu 22.04（aarch64）/ Linux x86_64 |
| ROS 2 | Humble |
| Python | 3.10（Ubuntu 22.04 系统自带） |
| **Node.js** | **v24.13.0（linux-x64，见 §2）** |
| npm / npx | 11.6.2（随 Node 24.13.0 附带） |

整机体检：

```bash
bash scripts/show_env.bash
```

---

## 2. Node.js 工具链（node / npm / npx）

`web/` 前端构建、ESLint、Prettier 以及部分 CI 脚本依赖 npm 生态，
必须在**非交互 shell** 中也能找到 `npx`。

### 2.1 一键初始化

```bash
# 诊断（只读，不改动任何文件）
bash scripts/node_env_init.bash --check

# 安装 / 修复（幂等，可重复执行）
bash scripts/node_env_init.bash

# 指定其他版本
bash scripts/node_env_init.bash --version 24.13.0

# 强制重装
bash scripts/node_env_init.bash --force
```

脚本做三件事：

1. 从 `https://nodejs.org/dist` 下载 `node-v24.13.0-linux-<arch>.tar.xz`
   （失败自动回退 `https://npmmirror.com/mirrors/node`），
   解压安装到 `~/.local/node/v24.13.0/`；
2. 把 `node`、`npm`、`npx`、`corepack` **软链**到 `/bin/sh` 默认 PATH 已包含的目录
   （依次探测 `~/.local/bin` → `~/bin` → `/usr/local/bin`）；
3. 幂等地向 `~/.bashrc` 与 `~/.profile` 追加 `PATH`（仅供交互 shell 使用）。

### 2.2 故障记录：`/bin/sh: 1: npx: not found`

> 记录时间：2026-10-05　环境：Linux x86_64　状态：已修复

#### 症状

Node.js 已安装且 `node -v` 正常，但在 IDE 任务 / 工具链自检里报：

```text
[ERROR] /bin/sh: 1: npx: not found
检测到本地环境未安装 npx 或 Node.js 版本过低，导致无法执行基于 npm 生态的工具链操作
```

#### 排查过程

```bash
$ ls -l ~/.local/node/v24.13.0/bin/
lrwxrwxrwx  node    -> ../lib/node_modules/...
lrwxrwxrwx  npm     -> ../lib/node_modules/npm/bin/npm-cli.js
lrwxrwxrwx  npx     -> ../lib/node_modules/npm/bin/npx-cli.js   # npx 确实存在

$ /bin/sh -c 'echo $PATH'
/home/aimer/.codebuddy-server-cn/bin/.../shim/safe-bin:
/home/aimer/.codebuddy-server-cn/bin/.../bin/remote-cli:
/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/home/aimer/bin:...   # ← 没有 node 目录
```

结论：`npx` 文件一直都在，**不是没装，是 PATH 没生效**。

#### 根因

`~/.bashrc` 里的 `export PATH=...` 只对 **bash 交互式 shell** 生效。
而 IDE 任务、构建脚本、CI、`sshd` 启动的会话走的是 **`/bin/sh` 非交互 shell**，
不读取 `~/.bashrc`（`.profile` 仅登录 shell 读取），因此完全看不到 Node 目录。

关键点：**「交互 shell 里能用」≠「工具链能用」**。
验证环境问题必须用非交互 shell 复现：

```bash
/bin/sh -c 'command -v npx'    # 这才是工具链视角
```

#### 修复

把命令软链到 `/bin/sh` 默认 PATH 已包含的目录（`~/bin`），而不是只改 `.bashrc`：

```bash
mkdir -p ~/bin
ln -sf ~/.local/node/v24.13.0/bin/node    ~/bin/node
ln -sf ~/.local/node/v24.13.0/bin/npm     ~/bin/npm
ln -sf ~/.local/node/v24.13.0/bin/npx     ~/bin/npx
ln -sf ~/.local/node/v24.13.0/bin/corepack ~/bin/corepack
```

该操作已固化进 `scripts/node_env_init.bash`，新机器执行一次即可。

#### 顺带发现的坑：追加配置时必须补换行

手工往 `~/.profile` 追加配置时，若文件末尾没有换行符，`>>` 会把新内容粘到上一行尾部：

```text
原文件最后一行:  fi
追加后变成:      fiexport PATH="$HOME/.local/node/v24.13.0/bin:$PATH"
```

`fiexport` 不是合法命令，`~/.profile` 直接语法错误，登录 shell 的 PATH 定制全部失效。
`scripts/node_env_init.bash` 已内置保护：追加前检测文件末尾是否为换行符。

#### 验收标准

| 检查项 | 命令 | 期望结果 |
| --- | --- | --- |
| 目标版本 | `~/.local/node/v24.13.0/bin/node -v` | `v24.13.0` |
| 非交互可见性 | `/bin/sh -c 'command -v npx'` | 输出非空路径 |
| 全套命令 | `bash scripts/node_env_init.bash --check` | `结果: OK` |
| 交互 shell | `bash -lc 'npx -v'` | `11.6.2` |
| 幂等性 | 连跑两次初始化脚本 | rc 文件不出现重复行 |
| rc 文件语法 | `bash -n ~/.bashrc && bash -n ~/.profile` | 无报错 |

---

## 3. 其他初始化脚本

| 脚本 | 作用 | 何时执行 |
| --- | --- | --- |
| `scripts/robot_env_init.bash` | 机器人主环境初始化 | 新机器首次部署 |
| `scripts/wsl_dev_env_init.bash` | WSL 开发环境初始化 | Windows 侧开发 |
| `scripts/ros2_communicate_env_init.bash` | ROS 2 通信环境（`PYTHONPATH`） | 编译/运行报找不到包时 |
| `scripts/ros2run_cli_env_init.bash` | 把 `scripts/` 加入 PATH，便于直接 `ros2 run` | 本地调试 ROS 2 节点 |
| `scripts/node_env_init.bash` | Node.js 工具链（见 §2） | 需要 npm/npx 时 |
| `scripts/cnb_credential_init.bash` | CNB Git 推送凭证（见 §6） | `git push` 报鉴权失败 |
| `scripts/setup_rdk.sh` | RDK X5 板级环境 | RDK 板上 |
| `bash init.bash` | OrbbecSDK / LDS50C SDK 拉取与依赖安装 | 首次拉取 SDK |
| `bash scripts/show_env.bash` | 环境体检（只读） | 排查任何环境问题前 |

> ⚠️ 环境初始化脚本普遍会修改 `~/.bashrc` / `~/.profile` / 系统配置。
> **执行前请先阅读脚本内容**，确认影响范围；脚本内的写操作应保持幂等，
> 便于在多台机器上重复执行。

---

## 4. 环境问题排查方法论

遇到「command not found」类问题，按此顺序定位：

```bash
# ① 目标 shell 视角：非交互 shell 到底能看见什么
/bin/sh -c 'echo $PATH'

# ② 命令是否真的存在
ls -l <可能的安装目录>/bin/<command>

# ③ 现有 shell 是否可见（对比交互与非交互）
command -v <command> && /bin/sh -c "command -v <command>"

# ④ 整机基线
bash scripts/show_env.bash
```

| 现象 | 优先怀疑 |
| --- | --- |
| 交互 shell 有、非交互 shell 没有 | PATH 只写在 `.bashrc`（本次故障） |
| 某机器有、另一台没有 | PATH 差异 / 装法不同，改用仓库内脚本统一 |
| `command not found` 但文件存在 | 权限不足（非 `+x`）、软链悬空、动态库缺失 |
| 工具链报「版本过低」 | 装了多个版本，`PATH` 里排在前面的不是目标版本 |

---

## 5. 维护约定：初始化问题必须记录

> **约定（项目级强制要求）**
>
> 1. 任何**开发环境初始化 / 环境故障排查**问题，无论大小，必须在**本文档**中留档，
>    不得只停留在终端历史、聊天记录或个人笔记里。
> 2. 记录必须包含以下五要素，缺一不可：
>    - **症状**：原始报错原文（复制粘贴，不要转述）；
>    - **排查过程**：执行过的命令与关键输出；
>    - **根因**：为什么会这样（而非「怎么解决的」）；
>    - **修复方式**：可复现的命令或脚本，优先沉淀成 `scripts/*_env_init.bash`；
>    - **验收标准**：可判定的检查命令与期望结果。
> 3. 若问题可脚本化，**必须**同步落地为 `scripts/` 下的幂等脚本，并在本文档登记。
> 4. 修复后**必须用非交互 shell 复验**（`/bin/sh -c '...'`），不能只在当前终端试一下。
> 5. 文档与脚本进仓库（`git add`），**不留在本地未提交状态**；机器专属路径不硬编码，
>    用 `$HOME`、`uname -m` 探测。

**新机器上手流程**：读本文档 → 跑 `scripts/show_env.bash` → 按需执行 `scripts/*_env_init.bash`。

---

## 6. CNB 凭证与 Git 推送鉴权

项目托管在 [CNB](https://cnb.cool/esjian/2026-Jic_Competiion_Code)。
IDE 内置 Git 与命令行 Git **不共享凭证**，推送鉴权失败时错误信息极具误导性。

### 6.1 症状

IDE 推送时日志出现（两种报错交替出现）：

```
remote: Unauthorized
fatal: Authentication failed for 'https://cnb.cool/esjian/2026-Jic_Competiion_Code.git/'

remote: Repository Not Found.
remote: 仓库不存在。
remote:
remote: token:
fatal: repository 'https://cnb.cool/esjian/2026-Jic_Competiion_Code.git/' not found
```

**误导性极强**：同一时刻 `git pull` 却是成功的（匿名可读，仓库为 Public），
容易误判为「仓库被删了」或「token 没配」，从而反复去重新申请/粘贴 token。

### 6.2 排查过程

```bash
# ① 确认 remote 干净、没有内嵌过期凭证
git remote -v | sed -E 's#(https?://)[^/@]*@#\1<credentials>@#g'

# ② 确认是否已有凭证助手（本案初始为空 → IDE 自行注入，故 CLI 也失败）
git config --get-all credential.helper || echo "(未设置 helper)"
ls -la ~/.git-credentials 2>/dev/null || echo "~/.git-credentials 不存在"

# ③ 直接问 CNB 要答案：git 推送端点对不同 Basic 组合的响应
CT=<token>
#    空密码 → 404「仓库不存在」；用户名密码都填 token → 200 git-receive-pack
curl -s -o /dev/null -w '%{http_code}\n' -u "$CT:" \
  "https://cnb.cool/esjian/2026-Jic_Competiion_Code.git/info/refs?service=git-receive-pack"
curl -s -o /dev/null -w '%{http_code}\n' -u "$CT:$CT" \
  "https://cnb.cool/esjian/2026-Jic_Competiion_Code.git/info/refs?service=git-receive-pack"
```

关键辅助命令：`GIT_TRACE_CURL=1 git push --dry-run` 可确认
`Authorization: Basic` 头**确实发出**了，从而把问题定位到服务端解析而非本地缺凭证。

### 6.3 根因

两个坑叠加，都与「凭证条目怎么写」有关：

1. **git 2.34 的 `credential-store` 会静默忽略没有 password 段的条目。**
   写 `https://<token>@cnb.cool`（只有 user）→ helper 匹配不到任何条目 →
   表现为 `fatal: could not read Username`，且**不给出任何显式报错**。
   必须写成 `https://<token>:@cnb.cool`（显式空密码）才会被匹配。
2. **CNB 要求 Basic 认证的用户名与密码都填 token。**
   即便条目被匹配上，`user=token, password=` 仍会被 CNB 判为
   「仓库不存在 / Repository Not Found」，`token:` 字段回显为空。

> 附带陷阱：多个 credential helper 同时存在时，**先返回结果的 helper 会短路**。
> 若全局 `~/.git-credentials` 里残留空密码条目，用 `-c credential.helper=...` 临时覆盖
> 也无效——必须先清理全局条目，否则会得出「改了没用」的错误结论。

### 6.4 修复方式

已沉淀为幂等脚本 `scripts/cnb_credential_init.bash`：

```bash
# 诊断（只读）
bash scripts/cnb_credential_init.bash --check

# 配置（token 从 CNB_TOKEN 环境变量读取，不入库、不进 remote URL）
CNB_TOKEN=<token> bash scripts/cnb_credential_init.bash
```

脚本做三件事：设置 `credential.helper=store` → 清理 `@cnb.cool` 旧条目 →
写入 `https://<token>:<token>@cnb.cool` 并将权限设为 `600`。

> ⚠️ token 明文落盘于 `~/.git-credentials`（权限 600），这是 git 标准做法。
> **不要**把 token 写进 remote URL 或仓库内任何文件（会随 `.git/config` 或代码泄露）。

### 6.5 验收标准

```bash
# ① 诊断脚本全绿
/bin/sh -c 'cd /home/aimer/Desktop/2026-Jic_Competiion_Code && bash scripts/cnb_credential_init.bash --check'
# 期望：两条 [OK]，无 [!] 警告

# ② 鉴权可达（不产生实际远程变更），退出码必须为 0
/bin/sh -c 'cd /home/aimer/Desktop/2026-Jic_Competiion_Code && GIT_TERMINAL_PROMPT=0 git push --dry-run origin HEAD:main'
# 期望：输出形如 'd94c01a..xxxxxxx  HEAD -> main'

# ③ 推送后本地与远端一致
git status -sb | head -1
# 期望：## main...origin/main（无 [ahead N]）
```

### 6.6 IDE 内推送仍失败时

脚本只修好**命令行 git**。若 IDE 推送依旧报错，说明 IDE 持有自己的一份旧凭证
并优先使用它——git 凭证助手无法覆盖，需在 IDE 设置中更新其内置的 CNB 凭证后重试。

---

## 7. 相关文档

| 文档 | 内容 |
| --- | --- |
| `docs/dev/instruction/hardware_config.md` | 硬件选型、接线定义 |
| `docs/dev/problem/compilation_issues.md` | 编译错误与依赖缺失 |
| `docs/dev/sop/fix-ide-extension-install-slow.md` | IDE 远程插件安装缓慢的排查与修复（网络/DNS/代理） |
| `docs/dev/instruction/project_structure.md` | 项目目录结构与分层架构 |
| `scripts/cnb_credential_init.bash` | CNB Git 凭证配置（见 §6） |
| `CONTRIBUTING.md` | 环境要求与提交前检查清单 |
