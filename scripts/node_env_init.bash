#!/bin/bash
# 安装并暴露 Node.js 工具链（node / npm / npx / corepack）到非交互 shell 可见的 PATH。
#
# 背景：项目 web/ 前端与 CI 工具链依赖 Node。本脚本解决两类问题：
#   1) 目标机器没有 Node，或版本不满足要求；
#   2) Node 装了，但只在 ~/.bashrc 里加了 PATH，导致 /bin/sh、IDE 任务、
#      sshd 非交互会话里 `npx: not found`。
#
# 用法：
#   bash scripts/node_env_init.bash            # 安装/修复（幂等）
#   bash scripts/node_env_init.bash --check    # 只诊断，不改动
#   bash scripts/node_env_init.bash --force    # 强制重装指定版本
#   bash scripts/node_env_init.bash --version 24.13.0   # 指定版本（默认 24.13.0）
#
# 幂等：已安装且软链正确时直接退出，不重复下载、不重复追加 ~/.bashrc。

set -euo pipefail

NODE_VERSION="${NODE_VERSION:-24.13.0}"
NODE_MIRROR="${NODE_MIRROR:-https://nodejs.org/dist}"
FALLBACK_MIRROR="https://npmmirror.com/mirrors/node"
INSTALL_ROOT="${NODE_INSTALL_ROOT:-$HOME/.local/node}"
CHECK_ONLY=0
FORCE=0

while [ $# -gt 0 ]; do
    case "$1" in
        --check)   CHECK_ONLY=1 ;;
        --force)   FORCE=1 ;;
        --version) NODE_VERSION="${2:?--version 需要参数}"; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
    shift
done

NODE_HOME="$INSTALL_ROOT/v$NODE_VERSION"
BIN_DIR="$NODE_HOME/bin"

# ---------------------------------------------------------------------------
# 选一个「非交互 shell 也能看到」的目录做软链目标。
# 优先级：~/.local/bin（部分发行版 /bin/sh 的默认 PATH 含 ~/.local/bin）
#         → ~/bin（多数 Linux 桌面环境含）
#         → /usr/local/bin（兜底，需要 sudo）
# ---------------------------------------------------------------------------
pick_link_dir() {
    local sh_path
    sh_path="$(/bin/sh -c 'echo $PATH' 2>/dev/null || echo "")"
    local d
    for d in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        case ":$sh_path:" in
            *":$d:"*) printf '%s' "$d"; return 0 ;;
        esac
    done
    for d in "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        [ -d "$d" ] && [ -w "$d" ] && { printf '%s' "$d"; return 0; }
    done
    printf '%s' "$HOME/bin"
}

check() {
    local ok=0
    echo "== Node.js 环境检查 (目标版本 v$NODE_VERSION) =="
    printf '安装目录     : %s\n' "$NODE_HOME"
    if [ -x "$BIN_DIR/node" ]; then
        printf '已安装版本   : %s\n' "$("$BIN_DIR/node" -v)"
    else
        echo "已安装版本   : <未安装>"
        ok=1
    fi

    local link_dir
    link_dir="$(pick_link_dir)"
    printf '软链目标目录 : %s\n' "$link_dir"

    local c
    for c in node npm npx corepack; do
        if /bin/sh -c "command -v $c" >/dev/null 2>&1; then
            printf '  %-9s : %s\n' "$c" "$(/bin/sh -c "command -v $c")"
        else
            printf '  %-9s : <不可见>  ← /bin/sh 下找不到\n' "$c"
            ok=1
        fi
    done

    if [ "$ok" -eq 0 ]; then
        echo "结果: OK"
    else
        echo "结果: 需要修复 → bash scripts/node_env_init.bash"
    fi
    return $ok
}

if [ "$CHECK_ONLY" -eq 1 ]; then
    check || true
    exit 0
fi

case "$(uname -m)" in
    x86_64)  NODE_ARCH=x64 ;;
    aarch64) NODE_ARCH=arm64 ;;
    *) echo "不支持的架构: $(uname -m)" >&2; exit 1 ;;
esac

TARBALL="node-v$NODE_VERSION-linux-$NODE_ARCH.tar.xz"

# ---------------------------------------------------------------------------
# 1. 安装到 ~/.local/node/v<version>
# ---------------------------------------------------------------------------
if [ "$FORCE" -eq 1 ]; then
    rm -rf "$NODE_HOME"
fi

if [ ! -x "$BIN_DIR/node" ]; then
    mkdir -p "$INSTALL_ROOT"
    TMP_TAR="$(mktemp -d)/$TARBALL"
    echo "→ 下载 $TARBALL"
    if ! curl -fsSL -o "$TMP_TAR" "$NODE_MIRROR/v$NODE_VERSION/$TARBALL"; then
        echo "→ 主源失败，回退镜像 $FALLBACK_MIRROR"
        curl -fsSL -o "$TMP_TAR" "$FALLBACK_MIRROR/v$NODE_VERSION/$TARBALL"
    fi
    echo "→ 解压到 $INSTALL_ROOT"
    tar -xJf "$TMP_TAR" -C "$INSTALL_ROOT"
    mv "$INSTALL_ROOT/node-v$NODE_VERSION-linux-$NODE_ARCH" "$NODE_HOME"
    rm -rf "$(dirname "$TMP_TAR")"
else
    echo "→ 已存在 $NODE_HOME，跳过下载"
fi

# ---------------------------------------------------------------------------
# 2. 软链到非交互 shell 可见的目录
# ---------------------------------------------------------------------------
LINK_DIR="$(pick_link_dir)"
mkdir -p "$LINK_DIR"
if [ ! -w "$LINK_DIR" ]; then
    echo "→ $LINK_DIR 不可写，请用 sudo 重跑本脚本" >&2
    exit 1
fi
echo "→ 软链 node/npm/npx/corepack 到 $LINK_DIR"
for c in node npm npx corepack; do
    ln -sfn "$BIN_DIR/$c" "$LINK_DIR/$c"
done

# ---------------------------------------------------------------------------
# 3. 交互 shell 便利项（幂等追加；非交互 shell 不依赖它）
#    注意：文件末尾可能没有换行，直接 >> 会把新行粘到上一行尾部，
#    曾因此在 ~/.profile 里生成出 `fiexport PATH=...` 这类坏行。
#    去重同时匹配绝对路径与 $HOME 写法，兼容历史手工添加的行。
# ---------------------------------------------------------------------------
ensure_path_line() {
    local rc="$1"
    [ -f "$rc" ] || touch "$rc"
    # 已有等价行（绝对路径或 $HOME 形式）则跳过
    if grep -qE "PATH=.*(\"|')?\$?\{?HOME\}?/?.local/node/v$NODE_VERSION/bin" "$rc"; then
        return 0
    fi
    [ -s "$rc" ] && [ -n "$(tail -c 1 "$rc")" ] && echo >> "$rc"
    echo "export PATH=\"\$HOME/.local/node/v$NODE_VERSION/bin:\$PATH\"" >> "$rc"
}

for rc in "$HOME/.bashrc" "$HOME/.profile"; do
    ensure_path_line "$rc"
done

echo "→ 验证"
check
