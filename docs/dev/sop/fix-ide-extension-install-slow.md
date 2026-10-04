# SOP：CodeBuddy IDE 远程插件安装缓慢的排查与修复

适用：通过 Remote-SSH 连到 Linux 开发机的 CodeBuddy IDE，安装扩展长时间停在 `Installing...`。

---

## 1. 症状

- 扩展点安装后长时间无响应，几分钟才完成，严重时最终失败并提示重试。
- 体积大的扩展尤其明显（例：`ms-vscode.cpptools` 的 VSIX 达 **115.5 MB**）。
- 同一网络下 `pip install`、`npm` 都很快，只有 IDE 插件慢。

---

## 2. 关键事实（与原版 VS Code 不同，先看这节）

| 事实 | 证据 |
| --- | --- |
| **CodeBuddy 的市场源不是 VS Code Marketplace，而是 `open-vsx.org`** | `/root/.codebuddy-server-cn/bin/stable-<commit>/product.json` 中 `"extensionsGallery": {"serviceUrl": "https://open-vsx.org/vscode/gallery", "itemUrl": "https://open-vsx.org/vscode/item"}` |
| **VSIX 由远端主机下载，不是本地 IDE** | 远端日志 `~/.codebuddy-server-cn/data/logs/<时间戳>/remoteagent.log`：`[info] Downloaded extension to file:///root/.codebuddy-server-cn/data/CachedExtensionVSIXs/...` |
| 扩展安装在远端 | `~/.codebuddy-server-cn/extensions/`（如 `ms-vscode.cpptools-1.35.2`） |
| 远端 agent 默认不用宿主代理 | extensionHost 启动参数含 `--useHostProxy=false` |
| 市场源无法从设置修改 | `extensionsGallery` 在 `product.json`（产品级），无 UI 入口；且 VS Code 市场客户端要求 serviceUrl 支持 CORS，`marketplace.visualstudio.com` 不允许跨域。**不要改它** |

**结论：优化本机网络与代理即可解决，不需要动 IDE 设置里的市场源。**

---

## 3. 根因

### 3.1 主因：`open-vsx.org` 直连跨境极慢

同一扩展包（`ms-python/vscode-python-envs`）实测：

| 路径 | TTFB | 结果 |
| --- | --- | --- |
| 直连 | **8.1s ~ 15.5s** | 一次 20.5s 后传输 **0 字节**（失败） |
| 经代理 `192.168.31.204:7890` | **0.71s** | 1.4 MB / 1.75s |

`open-vsx.org` 解析到 `151.101.x.x`（境外）。直连慢 + 偶发失败，IDE 侧表现为「失败 → 重试 → 再失败」，每次重试又是十几秒。

对照：`marketplace.visualstudio.com` 直连 TTFB 0.86s，`registry.npmmirror.com` 0.46s。

### 3.2 次因：IPv6 不可用但被优先使用

本机 `ip -6 addr show scope global` 无输出（无全局 IPv6），`curl -6` 直连立即失败；而 `marketplace.visualstudio.com` 同时返回 A 与 AAAA，解析器把 IPv6 排在前面，每次连接先撞不可达地址。

关键陷阱：发行版 `/etc/gai.conf` 里 `precedence ::ffff:0:0/96 100` 这一行**默认是注释**，等于从未生效。

### 3.3 次因：DNS 上游为家用路由器

原上游 `192.168.31.1`，对 `open-vsx.org` 出现过 `getaddrinfo EAI_AGAIN`，日志中留下多条 `Failed downloading vsix ... Retry again...`。

---

## 4. 三层修复（按持久化边界分开处理）

三层互不覆盖，任一生效即可解决；`git checkout` 只影响第 3 层。

```text
第 1 层  操作系统        /etc/gai.conf, /etc/systemd/resolved.d/     不受 git 影响
第 2 层  远端 server    ~/.codebuddy-server-cn/data/argv.json      不受 git 影响
第 3 层  工作区设置      .vscode/settings.json                      受 git 影响 → 需移出跟踪
```

### 第 1 层：操作系统网络

```bash
# 只诊断，不改系统
bash scripts/fix_vscode_extension_network.bash --check

# 应用修复（幂等，自动备份为 <path>.bak.<epoch>）
sudo bash scripts/fix_vscode_extension_network.bash

# 回滚
sudo bash scripts/fix_vscode_extension_network.bash --rollback
```

脚本做两件事：

1. 向 `/etc/gai.conf` 追加（带 `# managed-by:` 标记）：

   ```text
   precedence  ::ffff:0:0/96  100
   label       ::1/128        0
   label       ::/0           1
   ```

2. 写 `/etc/systemd/resolved.conf.d/99-fast-dns.conf`：`DNS=223.5.5.5 119.29.29.29 <本机默认网关>`（网关自动识别并保留，便于解析内网域名），重启 `systemd-resolved`；非 stub 环境则改写静态 `resolv.conf`。

> 可选 `--disable-ipv6`：**本机不推荐**。`sshd`、`x11vnc` 等监听在 `[::]:port` 双栈 socket 上，禁用后重启将只监听 IPv4，可能断掉远程连接。gai.conf 已足够。

### 第 2 层：让远端 server 走代理（关键，不受 git 影响）

两种写法，**都要做**，任一生效即可。

#### 2a. 环境变量（优先，实测更可靠）

远端 agent 的下载走 `getSystemProxyURI()`，它直接读**进程环境变量** `http_proxy` / `https_proxy`。server 由 sshd 非交互启动，会经 PAM 读取 `/etc/environment`，所以写在这里最稳：

```bash
cp -a /etc/environment /etc/environment.bak.$(date +%s)
cat >> /etc/environment <<'EOF'
http_proxy="http://192.168.31.204:7890"
https_proxy="http://192.168.31.204:7890"
no_proxy="localhost,127.0.0.1,::1,.local,192.168.31.0/24"
EOF
```

`no_proxy` 必须包含 `192.168.31.0/24`，否则本机 SSH 等回环/内联流量可能被绕进代理。

#### 2b. server 启动参数（补充）

`~/.codebuddy-server-cn/data/argv.json`（原本不存在，需新建）：

```json
{
  "http-proxy": "http://192.168.31.204:7890",
  "proxy-support": "override"
}
```

若 CodeBuddy 不识别该键，它只是一份无害配置，删掉即回滚。

**两层生效方式相同：必须重连 Remote-SSH**（断开远程窗口后重新连接，或重启本地 IDE）。server 进程是上一次会话遗留的（`ps` 显示已运行近 2 小时），不重连则参数与环境变量都不会变。

重连后验证：

```bash
# ① 环境变量是否进入 server 进程（最直接的证据）
tr '\0' '\n' < /proc/$(pgrep -f 'server-main.js' | head -1)/environ | grep -i proxy

# ② 启动参数是否带上（若 CodeBuddy 认 argv.json）
ps -eo args | grep -m1 'codebuddy-server-cn --start-server' | tr ' ' '\n' | grep proxy
```

### 第 3 层：工作区代理设置（易被 git 还原）

`.vscode/settings.json`：

```json
{
    "python-envs.defaultEnvManager": "ms-python.python:venv",
    "http.proxy": "http://192.168.31.204:7890",
    "http.proxySupport": "override"
}
```

**必须移出 git 跟踪**，否则任何 `git checkout .` / `git restore` / `git stash` 都会把它还原（本次故障即由此导致，当时 `git status` 完全干净）：

```bash
git rm --cached .vscode/settings.json      # 文件保留在工作区，IDE 照常读取
printf '\n# machine-specific IDE proxy config\n.vscode/settings.json\n' >> .git/info/exclude
```

用 `.git/info/exclude` 而非 `.gitignore`：前者是本仓库私有规则，不入库、不推送、不影响协作者。

---

## 5. 兜底：离线 VSIX 安装

`open-vsx.org` 是境外源，属「随时可能再坏」的外部依赖。当网络链路再次劣化，或想一次性装好大扩展时：

```bash
# 预设分组：python / cpp / all
python3 scripts/fetch_vsix.py --list-presets
python3 scripts/fetch_vsix.py --proxy http://192.168.31.204:7890 --preset all
python3 scripts/fetch_vsix.py ms-python.python ms-vscode.cpptools   # 也可指定单个
python3 scripts/fetch_vsix.py --dry-run ms-python.python             # 只查版本
```

- 走 Microsoft Marketplace（比 open-vsx 快），落到 `dist/vsix/`。
- 已验证单次 7 个扩展共 179 MB，经代理 4.3 MB/s；`cpptools` 115.5 MB 耗时 27 s。
- 安装：远端扩展面板 `...` → **Install from VSIX** → 选择 `dist/vsix/` 下文件。文件已在远端，全程不走网络。
- `dist/` 已写入 `.gitignore`。

---

## 6. 验收标准

| 检查项 | 期望结果 |
| --- | --- |
| `bash scripts/fix_vscode_extension_network.bash --check` | `gai.conf: IPv4 preferred [OK]`；`Current DNS Server: 223.5.5.5` |
| `open-vsx.org` 解析 | 5/5 成功，日志中不再出现 `EAI_AGAIN` |
| `ps -eo args \| grep codebuddy-server-cn` | 含 `--http-proxy`（重连后） |
| 安装时远端 `timeout 60 ss -tnp \| grep -E '7890\|open-vsx'` | remoteagent 连接打到 `192.168.31.204:7890` |
| `remoteagent.log` | 不再出现 `Failed downloading vsix ... Retry again` |

---

## 7. 回滚

```bash
sudo bash scripts/fix_vscode_extension_network.bash --rollback   # 第 1 层
# 第 2a 层：还原 /etc/environment
cp /etc/environment.bak.<epoch> /etc/environment
# 第 2b 层
rm /root/.codebuddy-server-cn/data/argv.json
# 第 3 层（恢复跟踪）
git checkout -- .vscode/settings.json && \
  sed -i '/.vscode\/settings.json/d' .git/info/exclude
```

---

## 8. 迁移到另一台机器

```bash
scp scripts/fix_vscode_extension_network.bash scripts/fetch_vsix.py <user>@<host>:/tmp/
ssh <user>@<host> 'bash /tmp/fix_vscode_extension_network.bash --check'   # 先看基线
ssh <user>@<host> 'sudo bash /tmp/fix_vscode_extension_network.bash'      # 第 1 层
# 第 2 层路径里的目录名按实际替换：
ssh <user>@<host> 'ls -d ~/.codebuddy-server* ~/.vscode-server*'
```

脚本会自动识别本机网关，无需手工改 DNS 列表。前提是该机存在可用代理（TCP 可连且能访问 `marketplace.visualstudio.com`）。
