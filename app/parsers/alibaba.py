"""
阿里系统一解析模块 — 淘宝 + 闲鱼
轻量模式：直抓网页信息
完整模式：复用 xianyu-auto-reply 的签名+Playwright（待接入）
"""

import re
import json
import requests
from config import XIANYU_API_URL, COOKIES
from browser import fetch_page, extract_meta_info, cookie_str_to_dict

UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36"
TIMEOUT = 15


def extract_item_id(url):
    """从淘宝/闲鱼链接提取商品ID"""
    # taobao: item.taobao.com/item.htm?id=xxx
    m = re.search(r'tao(?:bao)?\.com.*[?&]id=(\d+)', url)
    if m:
        return m.group(1), "taobao"

    # taobao short link: fetch page to find id
    if 'tb.cn' in url:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=10, allow_redirects=True)
            m = re.search(r'id[="\']+(\d{10,})', r.text[:10000])
            if m:
                return m.group(1), "taobao"
        except:
            pass

    # fallback: id= in URL params
    m = re.search(r'[?&]id=(\d+)', url)
    if m:
        return m.group(1), "taobao"

    # xianyu: goofish.com/item/xxx
    m = re.search(r'goofish\.com/item/(\d+)', url)
    if m:
        return m.group(1), "xianyu"

    return None, None


def parse_taobao_item(item_id):
    """解析淘宝商品（轻量版）"""
    result = {"item_id": item_id, "platform": "taobao", "source": "web_page"}

    # Try mobile page first (simpler HTML), then desktop
    for url in [
        f"https://m.taobao.com/item.htm?id={item_id}",
        f"https://item.taobao.com/item.htm?id={item_id}",
    ]:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code != 200:
                continue
            html = r.text

            m = re.search(r'<title>(.*?)</title>', html)
            if m:
                title = _clean(m.group(1))
                if title and title != "手机淘宝网":
                    result["title"] = title

            m = re.search(r'"price"[\s:]+"([^"]+)"', html)
            if m:
                result["price"] = m.group(1)

            m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
            if m:
                result["description"] = _clean(m.group(1))[:300]

            m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
            if m:
                result["image"] = m.group(1)

            if result.get("title") and result.get("title") != "手机淘宝网":
                return result
        except:
            pass


    # Browser fallback: use Playwright for JS-rendered pages
    try:
        tb_cookies = cookie_str_to_dict(COOKIES.get("taobao", ""))
        result_browser = fetch_page(f"https://item.taobao.com/item.htm?id={item_id}", cookies=tb_cookies, wait_seconds=5)
        if "error" not in result_browser:
            meta = extract_meta_info(result_browser.get("html", ""))
            if meta.get("title") and meta["title"] != "商品详情页":
                result["title"] = meta["title"]
            if meta.get("price"): result["price"] = meta["price"]
            if meta.get("description"): result["description"] = meta["description"]
            if meta.get("image"): result["image"] = meta["image"]
            result["source"] = "browser"
            if meta: return result
    except Exception:
        pass

    return {"error": "暂无法解析该淘宝商品", "item_id": item_id}


def parse_xianyu_item(item_id):
    """解析闲鱼商品"""
    result = {"item_id": item_id, "platform": "xianyu", "source": "web_page"}

    # Try external API if configured
    if XIANYU_API_URL:
        try:
            r = requests.get(f"{XIANYU_API_URL}/{item_id}",
                             headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == '200' and data.get('data'):
                    result.update({"detail": data['data'], "source": "api"})
                    return result
        except:
            pass

    # Parse from public page
    for url in [
        f"https://www.goofish.com/item/{item_id}",
        f"https://m.goofish.com/item?id={item_id}",
    ]:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            if r.status_code == 200:
                html = r.text
                m = re.search(r'<title>(.*?)</title>', html)
                if m:
                    result["title"] = _clean(m.group(1))
                m = re.search(r'["\']?price["\']?\s*[:=]\s*["\']?([\d.]+)', html)
                if m:
                    result["price"] = m.group(1)
                m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
                if m:
                    result["description"] = _clean(m.group(1))[:500]
                if result.get("title"):
                    return result
        except:
            pass


    # Browser fallback: use Playwright for JS-rendered pages
    try:
        xy_cookies = cookie_str_to_dict(COOKIES.get("xianyu", ""))
        result_browser = fetch_page(f"https://www.goofish.com/item/{item_id}", cookies=xy_cookies, wait_seconds=5)
        if "error" not in result_browser:
            meta = extract_meta_info(result_browser.get("html", ""))
            if meta.get("title"): result["title"] = meta["title"]
            if meta.get("price"): result["price"] = meta["price"]
            if meta.get("description"): result["description"] = meta["description"]
            result["source"] = "browser"
            if meta: return result
    except Exception:
        pass

    return {"error": "暂无法解析该闲鱼商品", "item_id": item_id}


def parse(url):
    """统一入口：自动识别淘宝/闲鱼"""
    item_id, platform = extract_item_id(url)
    if not item_id:
        return {"error": "无法提取商品ID"}

    if platform == "taobao":
        return parse_taobao_item(item_id)
    elif platform == "xianyu":
        return parse_xianyu_item(item_id)

    return {"error": "不支持的链接类型"}


def _clean(text):
    return re.sub(r'\s+', ' ', text).strip().replace('&#x0a;', '')
