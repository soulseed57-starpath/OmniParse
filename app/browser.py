"""
浏览器渲染模块
使用 Playwright 渲染 JavaScript 页面，支持可选 cookies
"""

import os
import time
import logging

logger = logging.getLogger("omniparse.browser")

_playwright_available = False
try:
    from playwright.sync_api import sync_playwright
    _playwright_available = True
except ImportError:
    pass


def fetch_page(url, cookies=None, wait_seconds=3, timeout_ms=15000):
    """
    使用无头浏览器获取 JS 渲染后的页面内容
    
    Args:
        url: 页面地址
        cookies: 可选，dict 格式的 cookies（用于登录态）
        wait_seconds: 渲染等待时间
        timeout_ms: 页面加载超时
    
    Returns:
        {"title": ..., "html": ..., "url": ...} 或 {"error": ...}
    """
    if not _playwright_available:
        return {"error": "Playwright 未安装，无法渲染页面"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 720}
            )

            # 如果有 cookies，设置到浏览器上下文
            if cookies:
                cookie_list = []
                for name, value in cookies.items():
                    cookie_list.append({
                        "name": name,
                        "value": value,
                        "domain": _get_domain(url),
                        "path": "/",
                    })
                context.add_cookies(cookie_list)
                logger.info(f"  已设置 {len(cookie_list)} 个 cookies")

            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                time.sleep(wait_seconds)
                content = page.content()
                title = page.title()
                return {"title": title, "html": content, "url": page.url}
            except Exception as e:
                return {"error": f"页面加载失败: {str(e)}"}
            finally:
                browser.close()
    except Exception as e:
        return {"error": f"浏览器启动失败: {str(e)}"}


def _get_domain(url):
    """从 URL 提取域名"""
    from urllib.parse import urlparse
    return urlparse(url).netloc


def cookie_str_to_dict(cookie_str):
    """将 cookie 字符串转为 dict（兼容多种格式）"""
    if not cookie_str:
        return {}
    cookies = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def extract_meta_info(html, fields=None):
    """从 HTML 中提取 meta 信息"""
    import re
    result = {}
    if fields is None:
        fields = ["title", "description", "price", "image"]
    m = re.search(r'<title>(.*?)</title>', html)
    if m and "title" in fields:
        result["title"] = _clean(m.group(1))
    m = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html)
    if m and "title" in fields and "title" not in result:
        result["title"] = _clean(m.group(1))
    m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
    if m and "description" in fields:
        result["description"] = _clean(m.group(1))[:500]
    m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
    if m and "image" in fields:
        result["image"] = m.group(1)
    m = re.search(r'"price"[:\s]+"([\d.]+)"', html)
    if m and "price" in fields:
        result["price"] = m.group(1)
    return result


def _clean(text):
    import re
    return re.sub(r'\s+', ' ', text).strip()
