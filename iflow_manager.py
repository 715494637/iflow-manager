#!/usr/bin/env python3
"""
iFlow 账号管理工具 - 交互式终端版
"""

import io
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Style

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

init(autoreset=True)

# API 配置
API_URL = "https://platform.iflow.cn/api/openapi/apikey"
PROFILE_URL = "https://platform.iflow.cn/profile"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://platform.iflow.cn",
}
PROFILE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
}
CONFIG_FILE = "accounts.json"

# 颜色定义
C = Fore
R = Style.RESET_ALL
B = Style.BRIGHT


def get_display_width(s):
    """计算字符串的实际显示宽度（中文占2个字符宽度）"""
    width = 0
    for char in s:
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width


def pad_string(s, width):
    """按显示宽度填充字符串，左对齐"""
    current_width = get_display_width(s)
    if current_width > width:
        result = ""
        w = 0
        for char in s:
            char_width = 2 if '\u4e00' <= char <= '\u9fff' else 1
            if w + char_width > width:
                break
            result += char
            w += char_width
        return result + ' ' * (width - w)
    return s + ' ' * (width - current_width)


def print_header(title):
    # 使用 ASCII 边框，和表格保持一致
    # 手动调整：emoji 实际占2格但 get_display_width 可能返回1
    width = 65
    title_width = get_display_width(title)
    # 如果标题包含 emoji，额外加1
    if any(ord(c) > 0x1F300 for c in title):
        title_width += 1
    padding = (width - title_width) // 2
    right_padding = width - padding - title_width
    print(f"\n{B}{C.CYAN}+{'-' * width}+{R}")
    print(f"{B}{C.CYAN}|{' ' * padding}{title}{' ' * right_padding}|{R}")
    print(f"{B}{C.CYAN}+{'-' * width}+{R}\n")


def print_menu(options, enabled=None):
    if enabled is None:
        enabled = list(options.keys())
    for k, v in options.items():
        if k in enabled:
            print(f"  {B}{C.WHITE}[{k}]{R} {v}")


def get_config_path():
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent.resolve()
    else:
        base_dir = Path(__file__).parent.resolve()
    return base_dir / CONFIG_FILE


def get_ccr_config_path():
    """获取 CCR 配置目录"""
    return Path.home() / ".claude-code-router" / "config.json"


def get_ccr_plugins_path():
    """获取 CCR plugins 目录"""
    return Path.home() / ".claude-code-router" / "plugins"


def get_ccr_status():
    """获取 CCR 文件状态"""
    paths = get_cross_platform_paths()
    system = platform.system()
    system_name = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(system, system)

    config_path = Path(paths["config_json"])
    header_path = Path(paths["header_js"])

    return {
        "system": system_name,
        "base_path": paths["base"],
        "config_exists": config_path.exists(),
        "config_path": str(config_path),
        "header_exists": header_path.exists(),
        "header_path": str(header_path),
    }


def load_accounts():
    config_path = get_config_path()
    if not config_path.exists():
        return {"accounts": []}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_accounts(data):
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_expire_time(expire_str):
    try:
        return datetime.strptime(expire_str, "%Y-%m-%d %H:%M")
    except:
        return None


def get_time_remaining(expire_str):
    expire_dt = parse_expire_time(expire_str)
    if not expire_dt:
        return "未知", "unknown"

    now = datetime.now()
    diff = expire_dt - now

    if diff.total_seconds() <= 0:
        return "已过期", "expired"

    days = diff.days
    hours = diff.seconds // 3600

    if days > 0:
        time_desc = f"{days}天{hours}时"
    elif hours > 0:
        time_desc = f"{hours}小时"
    else:
        time_desc = "<1小时"

    if days == 0:
        return time_desc, "expiring"
    return time_desc, "normal"


def fetch_profile_name(bxauth):
    """从 profile 页面获取账号名称"""
    import requests
    cookies = {"BXAuth": bxauth}

    try:
        response = requests.get(
            PROFILE_URL,
            headers=PROFILE_HEADERS,
            cookies=cookies,
            params={"tab": "apiKey"},
            timeout=30
        )
        print(f"{C.WHITE}[DEBUG] Profile 响应状态: {response.status_code}{R}")

        if response.status_code == 200:
            # 从 HTML 中提取手机号/账号名
            # 尝试匹配常见的手机号模式
            html = response.text

            # 尝试从页面提取手机号 (格式如 136****8852)
            match = re.search(r'(\d{3}\*{4}\d{4})', html)
            if match:
                name = match.group(1)
                print(f"{C.WHITE}[DEBUG] 从页面提取的账号名: {name}{R}")
                return name

            # 尝试其他模式
            match = re.search(r'"phone"\s*:\s*"([^"]+)"', html)
            if match:
                return match.group(1)

            match = re.search(r'"name"\s*:\s*"([^"]+)"', html)
            if match:
                return match.group(1)

            print(f"{C.WHITE}[DEBUG] 未找到账号名，使用默认值{R}")
            return "未知"
        print(f"{C.RED}获取 Profile 失败: {response.status_code}{R}")
    except Exception as e:
        print(f"{C.RED}获取 Profile 错误: {e}{R}")
    return "未知"


def fetch_api_key_info(bxauth):
    """获取 apiKey 和 expireTime（不获取 name）"""
    import requests
    cookies = {"BXAuth": bxauth}
    data = json.dumps({"name": ""}, separators=(',', ':'))

    try:
        response = requests.post(API_URL, headers=HEADERS, cookies=cookies, data=data, timeout=30)
        print(f"{C.WHITE}[DEBUG] API Key 响应状态: {response.status_code}{R}")
        print(f"{C.WHITE}[DEBUG] API Key 响应内容: {response.text[:200]}{R}")

        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("data"):
                data = result["data"]
                info = {
                    "apiKey": data.get("apiKey", ""),
                    "expireTime": data.get("expireTime", ""),
                }
                return info
        print(f"{C.RED}请求失败: {response.status_code}{R}")
    except Exception as e:
        print(f"{C.RED}网络错误: {e}{R}")
    return None


def update_ccr_config_and_restart():
    """更新 CCR 配置并执行 restart"""
    import requests

    ccr_path = get_ccr_config_path()
    print(f"{C.WHITE}[DEBUG] CCR 配置路径: {ccr_path}{R}")

    if not ccr_path.exists():
        print(f"{C.YELLOW}⚠️ CCR 配置不存在: {ccr_path}{R}")
        return False

    try:
        with open(ccr_path, "r", encoding="utf-8") as f:
            ccr_config = json.load(f)
    except Exception as e:
        print(f"{C.RED}读取 CCR 配置失败: {e}{R}")
        return False

    accounts_data = load_accounts()
    api_keys = ",".join([acc.get("apiKey", "") for acc in accounts_data.get("accounts", []) if acc.get("apiKey")])

    if not api_keys:
        print(f"{C.YELLOW}没有有效账号{R}")
        return False

    print(f"{C.WHITE}[DEBUG] API Keys 数量: {len(api_keys.split(','))}{R}")

    for provider in ccr_config.get("Providers", []):
        if provider.get("name") == "op-provider":
            provider["api_key"] = api_keys
            break
    else:
        ccr_config.setdefault("Providers", []).append({
            "name": "op-provider",
            "api_base_url": "https://apis.iflow.cn/v1/chat/completions",
            "api_key": api_keys,
            "models": ["qwen3-vl-plus", "minimax-m2.1", "kimi-k2.5", "glm-5", "minimax-m2.5"],
            "transformer": {"use": ["header"]}
        })

    try:
        with open(ccr_path, "w", encoding="utf-8") as f:
            json.dump(ccr_config, f, ensure_ascii=False, indent=2)
        print(f"{C.GREEN}✅ CCR 配置已更新{R}")
    except Exception as e:
        print(f"{C.RED}保存 CCR 配置失败: {e}{R}")
        return False

    # 执行 ccr restart
    print(f"\n{C.CYAN}🔄 正在执行 ccr restart...{R}")
    try:
        result = subprocess.run(
            "ccr restart",
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
            encoding="utf-8",
            errors="ignore"
        )
        if result.returncode == 0:
            print(f"{C.GREEN}✅ CCR 重启成功{R}")
            if result.stdout:
                print(f"{C.WHITE}--- 日志 ---{R}")
                print(result.stdout)
            return True
        else:
            print(f"{C.RED}❌ CCR 重启失败 (退出码: {result.returncode}){R}")
            if result.stderr:
                print(f"{C.RED}错误: {result.stderr}{R}")
            if result.stdout:
                print(f"{C.WHITE}输出: {result.stdout}{R}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{C.RED}❌ CCR 重启超时{R}")
        return False
    except FileNotFoundError:
        print(f"{C.YELLOW}⚠️ 未找到 ccr 命令，请确保已安装并配置在 PATH 中{R}")
        return False
    except Exception as e:
        print(f"{C.RED}❌ 执行失败: {e}{R}")
        return False


def get_cross_platform_paths():
    """获取跨平台的 CCR 路径"""
    system = platform.system()  # 'Windows', 'Darwin', 'Linux'
    username = os.getlogin()

    if system == 'Windows':
        base_path = f"C:/Users/{username}/.claude-code-router"
    elif system == 'Darwin':  # Mac
        base_path = f"/Users/{username}/.claude-code-router"
    else:  # Linux
        base_path = f"/home/{username}/.claude-code-router"

    return {
        "base": base_path,
        "plugins": f"{base_path}/plugins",
        "header_js": f"{base_path}/plugins/header.js",
        "config_json": f"{base_path}/config.json",
    }


def init_ccr_config():
    """初始化 CCR 配置"""
    import requests

    paths = get_cross_platform_paths()
    print(f"{C.WHITE}[DEBUG] 系统: {platform.system()}{R}")
    print(f"{C.WHITE}[DEBUG] 用户名: {os.getlogin()}{R}")
    print(f"{C.WHITE}[DEBUG] CCR 基础路径: {paths['base']}{R}")

    # 1. 创建 plugins 目录
    plugins_dir = Path(paths["plugins"])
    if not plugins_dir.exists():
        print(f"{C.CYAN}创建 plugins 目录...{R}")
        plugins_dir.mkdir(parents=True, exist_ok=True)

    # 2. 从 GitHub 获取 header.js
    header_js_url = "https://raw.githubusercontent.com/715494637/iflow-manager/refs/heads/master/ccr%20config/plugins/header.js"
    print(f"{C.CYAN}下载 header.js...{R}")
    try:
        response = requests.get(header_js_url, timeout=30)
        if response.status_code == 200:
            header_js_path = Path(paths["header_js"])
            with open(header_js_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"{C.GREEN}✅ header.js 已保存{R}")
        else:
            print(f"{C.RED}❌ 下载 header.js 失败: {response.status_code}{R}")
            return False
    except Exception as e:
        print(f"{C.RED}❌ 下载 header.js 错误: {e}{R}")
        return False

    # 3. 从 GitHub 获取 config.json 模板
    config_json_url = "https://raw.githubusercontent.com/715494637/iflow-manager/refs/heads/master/ccr%20config/config.json"
    print(f"{C.CYAN}下载 config.json 模板...{R}")
    try:
        response = requests.get(config_json_url, timeout=30)
        if response.status_code == 200:
            config_template = response.json()

            # 4. 修改 path 中的用户路径
            username = os.getlogin()
            for transformer in config_template.get("transformers", []):
                if "path" in transformer:
                    transformer["path"] = transformer["path"].replace("dypbi", username)

            # 5. 如有账号则添加 api_key，否则设为占位符
            accounts_data = load_accounts()
            accounts = accounts_data.get("accounts", [])

            api_keys = ",".join([acc.get("apiKey", "") for acc in accounts if acc.get("apiKey")])
            if not api_keys:
                api_keys = "YOUR_API_KEY_HERE"
                print(f"{C.YELLOW}⚠️ 没有账号，api_key 设为占位符{R}")
            else:
                print(f"{C.GREEN}✅ 找到 {len(accounts)} 个账号{R}")

            # 更新 provider 配置
            for provider in config_template.get("Providers", []):
                if provider.get("name") == "op-provider":
                    provider["api_key"] = api_keys
                    break

            # 6. 写入配置文件
            config_path = Path(paths["config_json"])
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_template, f, ensure_ascii=False, indent=2)

            print(f"{C.GREEN}✅ CCR 配置已初始化: {config_path}{R}")
            return True
        else:
            print(f"{C.RED}❌ 下载 config.json 失败: {response.status_code}{R}")
            return False
    except Exception as e:
        print(f"{C.RED}❌ 初始化 CCR 配置错误: {e}{R}")
        return False


def show_accounts(accounts):
    if not accounts:
        print(f"{C.YELLOW}暂无账号{R}")
        return 0, 0

    # 显示宽度定义（中文字符占2个宽度）
    w1 = 4   # 序号
    w2 = 13  # 账号（11字符手机号）
    w3 = 26  # API Key
    w4 = 16  # 过期时间
    w5 = 8   # 剩余

    # 表头使用 pad_string 处理中文宽度
    h1 = pad_string("序号", w1)
    h2 = pad_string("账号", w2)
    h3 = pad_string("API Key", w3)
    h4 = pad_string("过期时间", w4)
    h5 = pad_string("剩余", w5)

    # 边框宽度 = 显示宽度 + 2（左右各一个空格）
    top_border = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+{'-' * (w4 + 2)}+{'-' * (w5 + 2)}+"
    mid_border = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+{'-' * (w4 + 2)}+{'-' * (w5 + 2)}+"
    bot_border = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+{'-' * (w4 + 2)}+{'-' * (w5 + 2)}+"

    print(f"\n{B}{C.CYAN}{top_border}{R}")
    print(f"{B}{C.CYAN}| {h1} | {h2} | {h3} | {h4} | {h5} |{R}")
    print(f"{B}{C.CYAN}{mid_border}{R}")

    expired = expiring = 0

    for i, acc in enumerate(accounts, 1):
        name = acc.get("name", "") or "未知"
        api_key = acc.get("apiKey", "") or ""
        api_display = api_key[:20] + ".." if len(api_key) > 20 else api_key
        expire_time = acc.get("expireTime", "") or "未知"

        time_rem, status = get_time_remaining(acc.get("expireTime", ""))
        color = {"expired": C.RED, "expiring": C.YELLOW, "normal": C.GREEN}.get(status, C.WHITE)

        if status == "expired":
            expired += 1
        elif status == "expiring":
            expiring += 1

        # 内容行也使用 pad_string 处理中文宽度
        c1 = pad_string(str(i), w1)
        c2 = pad_string(name, w2)
        c3 = pad_string(api_display, w3)
        c4 = pad_string(expire_time, w4)
        c5 = pad_string(time_rem, w5)

        print(f"| {B}{c1}{R} | {B}{C.GREEN}{c2}{R} | {B}{C.BLUE}{c3}{R} | {C.MAGENTA}{c4}{R} | {color}{c5}{R} |")

    print(f"{B}{C.CYAN}{bot_border}{R}")
    return expired, expiring


def input_choice(prompt, choices):
    while True:
        choice = input(f"{B}{prompt}{R}").strip()
        if choice in choices:
            return choice
        print(f"{C.RED}无效选项，请重试{R}")


def input_text():
    return input().strip()


def input_yesno(prompt, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        choice = input(f"{B}{prompt}{suffix}{R}").strip().lower()
        if not choice:
            return default
        if choice in ['y', 'yes', '是']:
            return True
        if choice in ['n', 'no', '否']:
            return False
        print(f"{C.RED}请输入 y 或 n{R}")


def smart_update_accounts(accounts_data, accounts):
    """智能更新 - 只更新快过期的账号的 apiKey 和 expireTime"""
    if not accounts:
        print(f"{C.YELLOW}没有可更新的账号{R}")
        return 0

    to_update = []
    for i, acc in enumerate(accounts):
        time_rem, status = get_time_remaining(acc.get("expireTime", ""))
        if status in ["expired", "expiring"]:
            to_update.append(i)

    if not to_update:
        print(f"{C.GREEN}所有账号都正常，无需更新{R}")
        return 0

    print(f"\n{C.YELLOW}检测到 {len(to_update)} 个账号即将过期/已过期{R}")
    if not input_yesno("是否更新这些账号？"):
        return 0

    success = 0
    for idx in to_update:
        name = accounts[idx].get("name", "未知")
        print(f"  🔄 正在更新 {name}...", end=" ", flush=True)
        info = fetch_api_key_info(accounts[idx].get("BXAuth", ""))
        if info:
            # 只更新 apiKey 和 expireTime，不更新 name
            accounts[idx]["apiKey"] = info["apiKey"]
            accounts[idx]["expireTime"] = info["expireTime"]
            print(f"{C.GREEN}✅{R}")
            success += 1
        else:
            print(f"{C.RED}❌{R}")

    save_accounts(accounts_data)
    print(f"{C.GREEN}更新完成: {success}/{len(to_update)}{R}")
    return success


def force_update_all_accounts(accounts_data, accounts):
    """强制更新全部账号的 apiKey 和 expireTime"""
    if not accounts:
        print(f"{C.YELLOW}没有可更新的账号{R}")
        return 0

    success = 0
    for idx, acc in enumerate(accounts):
        name = acc.get("name", "未知")
        print(f"  🔄 正在更新 {name}...", end=" ", flush=True)
        info = fetch_api_key_info(acc.get("BXAuth", ""))
        if info:
            # 只更新 apiKey 和 expireTime，不更新 name
            accounts[idx]["apiKey"] = info["apiKey"]
            accounts[idx]["expireTime"] = info["expireTime"]
            print(f"{C.GREEN}✅{R}")
            success += 1
        else:
            print(f"{C.RED}❌{R}")

    save_accounts(accounts_data)
    print(f"{C.GREEN}强制更新完成: {success}/{len(accounts)}{R}")
    return success


def delete_account(accounts_data, accounts):
    """删除账号"""
    if not accounts:
        return False

    print(f"\n{B}请选择要删除的账号:{R}")
    for i, acc in enumerate(accounts, 1):
        print(f"  {i}. {acc.get('name', '未知')}")

    print(f"{B}序号: {R}", end="")
    idx = input_text()
    try:
        idx = int(idx) - 1
        if 0 <= idx < len(accounts):
            name = accounts[idx].get("name", "未知")
            if input_yesno(f"确定删除 {name}？", default=False):
                accounts.pop(idx)
                save_accounts(accounts_data)
                print(f"{C.GREEN}✅ 已删除{R}")
                return True
    except:
        pass
    return False


def main():
    while True:
        accounts_data = load_accounts()
        accounts = accounts_data.get("accounts", [])

        print_header("📋 iFlow 账号管理")
        expired, expiring = show_accounts(accounts)

        # 显示 CCR 状态（简洁版）
        ccr_status = get_ccr_status()
        config_status = f"{C.GREEN}OK{R}" if ccr_status['config_exists'] else f"{C.RED}X{R}"
        header_status = f"{C.GREEN}OK{R}" if ccr_status['header_exists'] else f"{C.RED}X{R}"

        print(f"\n{B}{C.CYAN}[ CCR Status ]{R}")
        print(f"  {B}Platform{R}: {ccr_status['system']}")
        print(f"  {B}Config {config_status}{R} | {B}Header {header_status}{R}")
        print(f"  {B}Path{R}: {ccr_status['base_path']}")

        # 操作菜单
        print(f"\n{B}请选择操作:{R}")
        print_menu({
            "1": "➕ 添加账号",
            "2": "🔄 智能续期",
            "3": "⚡ 全部续期",
        })
        if accounts:
            print_menu({
                "4": "🗑️ 删除账号",
            })
        print_menu({
            "5": "⚙️ 更新CCR配置",
            "6": "🔧 初始化CCR配置",
            "7": "🚪 退出",
        })

        choices = ["1", "2", "3", "5", "6", "7"] if not accounts else ["1", "2", "3", "4", "5", "6", "7"]
        choice = input_choice("\n请输入选项：", choices)

        if choice == "1":
            # 添加账号
            print(f"\n{C.CYAN}请输入 BXAuth（浏览器开发者工具 → Application → Cookies → BXAuth）{R}")
            print(f"{B}输入: {R}", end="")
            bxauth = input_text()
            if not bxauth:
                print(f"{C.RED}BXAuth 不能为空{R}")
                continue

            # 先获取 name
            print(f"{C.BLUE}正在获取账号名称...{R}")
            name = fetch_profile_name(bxauth)

            # 再获取 apiKey 和 expireTime
            print(f"{C.BLUE}正在获取 API Key...{R}")
            info = fetch_api_key_info(bxauth)
            if info:
                accounts.append({
                    "BXAuth": bxauth,
                    "apiKey": info["apiKey"],
                    "name": name,
                    "expireTime": info["expireTime"],
                })
                save_accounts(accounts_data)
                print(f"{C.GREEN}✅ 添加成功: {name}{R}")

                # 自动更新 CCR
                print(f"\n{C.CYAN}自动更新 CCR 配置...{R}")
                update_ccr_config_and_restart()
            else:
                print(f"{C.RED}获取 API Key 失败{R}")

        elif choice == "2":
            success = smart_update_accounts(accounts_data, accounts)
            if success > 0:
                print(f"\n{C.CYAN}自动更新 CCR 配置...{R}")
                update_ccr_config_and_restart()

        elif choice == "3":
            success = force_update_all_accounts(accounts_data, accounts)
            if success > 0:
                print(f"\n{C.CYAN}自动更新 CCR 配置...{R}")
                update_ccr_config_and_restart()

        elif choice == "4":
            if delete_account(accounts_data, accounts):
                print(f"\n{C.CYAN}自动更新 CCR 配置...{R}")
                update_ccr_config_and_restart()

        elif choice == "5":
            update_ccr_config_and_restart()

        elif choice == "6":
            print(f"\n{C.CYAN}初始化 CCR 配置...{R}")
            if init_ccr_config():
                print(f"{C.GREEN}✅ CCR 初始化完成{R}")
            else:
                print(f"{C.RED}❌ CCR 初始化失败{R}")

        elif choice == "7":
            print(f"{C.CYAN}再见喵～ 🐱{R}")
            break

        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.CYAN}再见喵～ 🐱{R}")
