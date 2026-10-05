#!/bin/bash
# 配置 CNB (cnb.cool) 的 Git HTTPS 凭证，使 IDE / CLI 的 git push 能通过鉴权。
#
# 背景：项目托管在 CNB。IDE 内置 Git 与命令行 git 默认不共享凭证，
#       推送时报 `remote: Unauthorized` 或 `remote: 仓库不存在 / Repository Not Found`，
#       但 `git pull` 又能匿名成功，极易误判为「仓库没了」或「token 没配」。
#
# 本脚本解决两个坑（均为实测踩坑，见 docs/dev/instruction/dev_env_init.md §6）：
#   1) 凭证条目格式：git 2.34 的 credential-store 会**静默忽略**只有 user、没有 pass 的
#      `https://<token>@cnb.cool`，必须写 `https://<token>:<token>@cnb.cool`；
#   2) CNB 要求 Basic 认证的**用户名与密码都填 token**，空密码会被判为「仓库不存在」。
#
# 用法：
#   bash scripts/cnb_credential_init.bash                      # 从环境变量 CNB_TOKEN 读取
#   CNB_TOKEN=xxx bash scripts/cnb_credential_init.bash        # 显式传入
#   bash scripts/cnb_credential_init.bash --check              # 只诊断，不改动任何文件
#
# 幂等：凭证已正确且 helper 已配置时直接退出，不重复写文件。
# 安全：token 明文落盘于 ~/.git-credentials，权限强制 600。
#       不把 token 写进仓库内任何文件，也不写进 remote URL。

set -euo pipefail

CNB_HOST="${CNB_HOST:-cnb.cool}"
CRED_FILE="${CRED_FILE:-$HOME/.git-credentials}"
CHECK_ONLY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --check)  CHECK_ONLY=1 ;;
        -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
    shift
done

ok()   { printf '\033[32m[OK]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 期望的凭证行：用户名与密码都必须是 token -------------------------------
expected_line() {
    printf 'https://%s:%s@%s\n' "$1" "$1" "$CNB_HOST"
}

# --- 诊断 -------------------------------------------------------------------
current_helper="$(git config --global --get credential.helper 2>/dev/null || true)"
if [ -f "$CRED_FILE" ]; then
    current_line="$(grep -m1 -F "https://" "$CRED_FILE" || true)"
else
    current_line=""
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "== CNB Git 凭证诊断 =="
    echo "凭证文件      : $CRED_FILE"
    [ -f "$CRED_FILE" ] && echo "文件权限      : $(stat -c '%a' "$CRED_FILE")" \
                       || echo "文件状态      : 不存在"
    echo "credential.helper : ${current_helper:-<未配置>}"
    # 判断现有条目是否为 CNB 可用的 token:token 形式
    if printf '%s' "$current_line" | grep -qE '^https://[^:@]+:[^:@]+@[^/]+$'; then
        ok "凭证条目为 token:token 形式（CNB 可用）"
    elif [ -n "$current_line" ]; then
        warn "凭证条目缺少 password 段，git 2.34 会静默忽略 → 需重写为 token:token"
    else
        warn "未找到凭证条目"
    fi
    if [ "$current_helper" = "store" ]; then
        ok "credential.helper = store"
    else
        warn "credential.helper 应为 store，当前为 ${current_helper:-<未配置>}"
    fi
    exit 0
fi

# --- 写入 -------------------------------------------------------------------
[ -n "${CNB_TOKEN:-}" ] || die "未提供 token。请用 CNB_TOKEN=xxx bash $0 执行"

expected="$(expected_line "$CNB_TOKEN")"

if [ "$current_helper" != "store" ]; then
    git config --global credential.helper store
    ok "已设置 credential.helper = store"
fi

# 先备份旧文件（仅在内容确实要变时）
if [ -f "$CRED_FILE" ] && [ "$current_line" != "$expected" ]; then
    cp "$CRED_FILE" "$CRED_FILE.bak.$(date +%Y%m%d%H%M%S)"
    warn "原凭证文件已备份"
fi

# 幂等：内容一致则不写
if [ "$current_line" = "$expected" ]; then
    chmod 600 "$CRED_FILE"
    ok "凭证已正确且为 token:token 形式，无需改动"
else
    # 过滤掉旧的 cnb.cool 条目后重写，避免残留空密码条目抢先匹配
    tmp="$(mktemp)"
    if [ -f "$CRED_FILE" ]; then
        grep -v -F "@$CNB_HOST" "$CRED_FILE" > "$tmp" 2>/dev/null || true
    fi
    printf '%s\n' "$expected" >> "$tmp"
    # umask 保证创建时即为 600
    ( umask 077 && cat "$tmp" > "$CRED_FILE" )
    rm -f "$tmp"
    ok "已写入 token:token 格式凭证"
fi

chmod 600 "$CRED_FILE"
ok "凭证文件权限已设为 600"

cat <<EOF

== 下一步 ==
1. 验证鉴权（不会真正推送）：
     /bin/sh -c 'cd $(git -C . rev-parse --show-toplevel 2>/dev/null || pwd) && GIT_TERMINAL_PROMPT=0 git push --dry-run origin HEAD:main'
   期望输出形如：'d94c01a..xxxxxxx  HEAD -> main'，且退出码为 0。
2. IDE 内推送若仍失败，请在 IDE 设置里更新其内置的 CNB 凭证后重试。

注意：IDE 可能持有自己的一份旧凭证并优先使用，git 凭证助手无法覆盖它。
EOF
