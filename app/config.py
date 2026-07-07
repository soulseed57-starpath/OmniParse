"""
配置管理 — 单一配置源，所有解析器从这里读取
支持可选 cookies 配置，用于需要登录的平台
"""

import os
from pathlib import Path

CONFIG_FILE = Path("/app/config.yaml")
TEMPLATE = """# OmniParse 配置文件
# 首次启动自动生成，用户按需填写

# 【必填】内容解析服务 API 地址
# 部署 Douyin_TikTok_Download_API 后填写:
parser_api_url: ""

# 【可选】服务端口（默认 8000）
port: 8000

# 【可选】浏览器 cookies — 不填使用公开解析，数据有限
# 配置后可用 Playwright 获取更完整的页面内容
# 从浏览器登录后导出 cookie 字符串填入即可
cookies:
  douyin: ""
  taobao: ""
  xianyu: ""
"""

# ─── 解析器使用的配置（由 check_config 填充） ────────
PARSER_API_URL = ""
PORT = "8000"
XIANYU_API_URL = ""

# Cookies 配置（各平台可选）
COOKIES = {
    "douyin": "",
    "taobao": "",
    "xianyu": "",
}


def check_config():
    """检查配置，填充全局变量"""
    global PARSER_API_URL, PORT, XIANYU_API_URL, COOKIES

    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(TEMPLATE)
        print(f"\n⚠️  首次启动，已生成配置模板: {CONFIG_FILE}")
        print("   请填写必要配置后重启服务。\n")
        print(TEMPLATE)
        return False

    # 读取配置（兼容简单 key:value 和嵌套结构）
    config = {}
    current_section = None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("#") or not line:
                continue
            if ":" not in line:
                continue
            indent = len(line) - len(line.lstrip())
            key, val = [x.strip() for x in line.split(":", 1)]
            if indent == 0 and val == "" and key != "":
                # 新章节开始
                current_section = key
                config[current_section] = {}
            elif indent > 0 and current_section:
                # 嵌套值
                config[current_section][key] = val.strip('"').strip("'")
            else:
                # 顶层值
                config[key] = val.strip('"').strip("'")

    if not config.get("parser_api_url"):
        print(f"\n❌ 配置不完整，缺少 parser_api_url")
        print(f"   请编辑: {CONFIG_FILE}")
        return False

    # 填充全局变量
    PARSER_API_URL = config["parser_api_url"].rstrip("/")
    PORT = config.get("port", "8000")
    XIANYU_API_URL = config.get("xianyu_api_url", "")

    # 读取 cookies（可选）
    cookies_config = config.get("cookies", {})
    if cookies_config:
        for platform in ["douyin", "taobao", "xianyu"]:
            if cookies_config.get(platform):
                COOKIES[platform] = cookies_config[platform]

    # 输出状态（隐藏完整 cookie）
    for k, v in COOKIES.items():
        if v:
            print(f"  🍪 {k}: 已配置 ({v[:20]}...)")
        else:
            print(f"  🍪 {k}: 未配置（使用公开解析）")

    # 同时设环境变量（兼容其他工具）
    os.environ["PARSER_API_URL"] = PARSER_API_URL
    os.environ["PORT"] = PORT
    if XIANYU_API_URL:
        os.environ["XIANYU_API_URL"] = XIANYU_API_URL

    return True
