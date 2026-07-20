# -*- coding: utf-8 -*-
"""
星河 API 凭证配置向导

运行此脚本为当前用户配置星河 API 凭证。
每个人必须使用自己的凭证，不可混用。

使用方法:
    python setup.py
"""

import os
import sys
import hashlib
import time
import platform


def get_shell_profile_path():
    """根据操作系统和 shell 类型，返回配置文件路径"""
    home = os.path.expanduser("~")
    system = platform.system()

    if system == "Windows":
        # Git Bash / MSYS2
        bashrc = os.path.join(home, ".bashrc")
        if os.path.exists(bashrc):
            return bashrc
        # PowerShell profile
        ps_profile = os.path.join(home, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")
        return bashrc  # default to .bashrc
    else:
        # macOS / Linux
        zshrc = os.path.join(home, ".zshrc")
        bashrc = os.path.join(home, ".bashrc")
        if os.path.exists(zshrc):
            return zshrc
        return bashrc


def check_existing():
    """检查是否已经配置了环境变量"""
    user = os.environ.get("XINGHE_CLIENT_USER")
    secret = os.environ.get("XINGHE_CLIENT_SECRET")
    oa = os.environ.get("XINGHE_OA")

    if user and secret and oa:
        print(f"  当前已配置:")
        print(f"    XINGHE_CLIENT_USER = {user}")
        print(f"    XINGHE_OA          = {oa}")
        print(f"    XINGHE_CLIENT_SECRET = {'*' * len(secret)}")
        return True
    return False


def test_connection(user, secret, oa):
    """测试凭证是否能连通星河 API"""
    try:
        import requests
    except ImportError:
        print("  [跳过] 未安装 requests，无法测试连通性")
        return None

    api_base = "https://58dp.58corp.com/openapi"
    ts = str(int(time.time() * 1000))
    token = hashlib.md5((secret + ts).encode()).hexdigest()

    headers = {
        "client-user": user,
        "ts": ts,
        "token": token,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{api_base}/team/doc/run",
            headers=headers,
            json={"oa": oa, "content": "SELECT 1", "sql_engine": 4},
            timeout=15,
        )
        result = resp.json()
        if result.get("code") == 0:
            return True
        else:
            print(f"  API 返回错误: code={result.get('code')}, msg={result.get('msg')}")
            return False
    except Exception as e:
        print(f"  连接失败: {e}")
        return False


def main():
    print("=" * 50)
    print("  星河 API 凭证配置向导")
    print("=" * 50)
    print()
    print("  每个团队成员必须配置自己的凭证。")
    print("  凭证从星河 API 管理平台申请:")
    print("  https://dp.58corp.com/api-manage/service-list")
    print()

    if check_existing():
        print()
        choice = input("  已有配置，是否重新设置？(y/N): ").strip().lower()
        if choice != "y":
            print("  保持现有配置，退出。")
            return

    print()
    print("  请输入你的凭证信息:")
    print()

    client_user = input("  服务账号 (XINGHE_CLIENT_USER): ").strip()
    if not client_user:
        print("  服务账号不能为空，退出。")
        return

    client_secret = input("  调用密码 (XINGHE_CLIENT_SECRET): ").strip()
    if not client_secret:
        print("  调用密码不能为空，退出。")
        return

    oa = input("  你的 OA 账号 (XINGHE_OA): ").strip()
    if not oa:
        print("  OA 账号不能为空，退出。")
        return

    # 测试连通性
    print()
    print("  正在测试连接...")
    ok = test_connection(client_user, client_secret, oa)
    if ok is True:
        print("  连接成功!")
    elif ok is False:
        print("  连接失败，请检查凭证是否正确。")
        choice = input("  是否仍然保存配置？(y/N): ").strip().lower()
        if choice != "y":
            return

    # 写入 shell 配置文件
    profile_path = get_shell_profile_path()
    env_lines = f"""
# === 星河 API 凭证 (由 setup.py 配置) ===
export XINGHE_CLIENT_USER="{client_user}"
export XINGHE_CLIENT_SECRET="{client_secret}"
export XINGHE_OA="{oa}"
"""

    print()
    print(f"  将写入到: {profile_path}")
    print()
    confirm = input("  确认写入？(Y/n): ").strip().lower()
    if confirm == "n":
        print()
        print("  你也可以手动添加以下内容到你的 shell 配置文件:")
        print(env_lines)
        return

    # 检查是否已有旧配置，替换而非追加
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 移除旧的配置块
        lines = content.split("\n")
        new_lines = []
        skip = False
        for line in lines:
            if "星河 API 凭证" in line:
                skip = True
                continue
            if skip and line.startswith("export XINGHE_"):
                continue
            skip = False
            new_lines.append(line)
        content = "\n".join(new_lines)
    else:
        content = ""

    with open(profile_path, "a" if not content.strip() else "w", encoding="utf-8") as f:
        if content.strip():
            f.write(content.rstrip("\n") + "\n")
        f.write(env_lines)

    print()
    print("  配置完成!")
    print(f"  请运行以下命令使配置生效:")
    print(f"    source {profile_path}")
    print()
    print("  或者重新打开终端。")


if __name__ == "__main__":
    main()
