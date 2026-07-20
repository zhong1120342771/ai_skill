# -*- coding: utf-8 -*-
"""
将星河凭证持久化保存到当前用户的环境变量中。
供 Claude 在聊天中自动调用，用户无需手动操作。

用法:
    python save_credentials.py <client_user> <client_secret> <oa>

效果:
    - Windows: 用 setx 写入用户级永久环境变量（新开的所有终端/程序都能读到）
    - macOS/Linux: 写入 ~/.zshrc 或 ~/.bashrc
    - 同时输出 export 命令供当前 session 立即生效
"""

import os
import sys
import subprocess
import platform
import hashlib
import time


def is_windows():
    return platform.system() == "Windows" or os.name == "nt" or "MINGW" in os.environ.get("MSYSTEM", "")


def test_connection(user, secret, oa):
    """快速验证凭证是否有效"""
    try:
        import requests
        ts = str(int(time.time() * 1000))
        token = hashlib.md5((secret + ts).encode()).hexdigest()
        resp = requests.post(
            "https://58dp.58corp.com/openapi/team/doc/run",
            headers={"client-user": user, "ts": ts, "token": token, "Content-Type": "application/json"},
            json={"oa": oa, "content": "SELECT 1", "sql_engine": 4},
            timeout=15,
        )
        return resp.json().get("code") == 0
    except Exception:
        return None


def save_windows(client_user, client_secret, oa):
    """Windows: 用 setx 写入用户级永久环境变量"""
    pairs = {
        "XINGHE_CLIENT_USER": client_user,
        "XINGHE_CLIENT_SECRET": client_secret,
        "XINGHE_OA": oa,
    }
    for key, val in pairs.items():
        result = subprocess.run(
            ["setx", key, val],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            print(f"WARNING: setx {key} failed: {result.stderr.strip()}")
        else:
            print(f"  setx {key} = OK")

    # 同时写入 .bashrc 以兼容 Git Bash
    home = os.path.expanduser("~")
    bashrc = os.path.join(home, ".bashrc")
    _write_shell_profile(bashrc, client_user, client_secret, oa)

    return "Windows registry (setx) + " + bashrc


def save_unix(client_user, client_secret, oa):
    """macOS/Linux: 写入 shell 配置文件"""
    home = os.path.expanduser("~")
    profile = None
    for name in [".zshrc", ".bashrc", ".bash_profile"]:
        path = os.path.join(home, name)
        if os.path.exists(path):
            profile = path
            break
    if not profile:
        profile = os.path.join(home, ".bashrc")

    _write_shell_profile(profile, client_user, client_secret, oa)
    return profile


def _write_shell_profile(profile, client_user, client_secret, oa):
    """写入 shell 配置文件，替换已有的星河配置块"""
    env_block = (
        '\n# === Xinghe API Credentials ===\n'
        f'export XINGHE_CLIENT_USER="{client_user}"\n'
        f'export XINGHE_CLIENT_SECRET="{client_secret}"\n'
        f'export XINGHE_OA="{oa}"\n'
    )

    if os.path.exists(profile):
        with open(profile, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        new_lines = []
        skip = False
        for line in lines:
            if "Xinghe API Credentials" in line:
                skip = True
                continue
            if skip and line.strip().startswith("export XINGHE_"):
                continue
            if skip:
                skip = False
            new_lines.append(line)
        content = "".join(new_lines).rstrip("\n") + "\n"
    else:
        content = ""

    with open(profile, "w", encoding="utf-8") as f:
        f.write(content + env_block)


def main():
    if len(sys.argv) != 4:
        print("ERROR: usage: python save_credentials.py <client_user> <client_secret> <oa>")
        sys.exit(1)

    client_user, client_secret, oa = sys.argv[1], sys.argv[2], sys.argv[3]

    # 1. 验证凭证
    print(f"VERIFY: testing connection for OA={oa} ...")
    ok = test_connection(client_user, client_secret, oa)
    if ok is True:
        print("VERIFY: OK")
    elif ok is False:
        print("VERIFY: FAILED - credentials may be incorrect")
        sys.exit(2)
    else:
        print("VERIFY: SKIPPED - could not reach API (network issue?)")

    # 2. 持久化保存
    if is_windows():
        location = save_windows(client_user, client_secret, oa)
    else:
        location = save_unix(client_user, client_secret, oa)
    print(f"SAVED: {location}")

    # 3. 输出 export 命令供当前 shell session 立即生效
    print(f'EXPORT: export XINGHE_CLIENT_USER="{client_user}" XINGHE_CLIENT_SECRET="{client_secret}" XINGHE_OA="{oa}"')


if __name__ == "__main__":
    main()
