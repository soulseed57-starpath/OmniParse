"""
抖音解析模块
"""

import re
import requests
from config import PARSER_API_URL, COOKIES
from browser import fetch_page, cookie_str_to_dict

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 30


def _req(url, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        return r
    except Exception:
        return None


def extract_video_id(url):
    m = re.search(r'douyin\.com/video/(\d+)', url)
    if m:
        return m.group(1)
    try:
        r = requests.head(url, allow_redirects=True, timeout=10, headers={"User-Agent": UA})
        m = re.search(r'douyin\.com/video/(\d+)', r.url)
        if m:
            return m.group(1)
    except:
        pass
    return None


def parse_douyin_video(url):
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "无法提取视频ID"}

    resp = _req(f"{PARSER_API_URL}/api/douyin/web/fetch_one_video?aweme_id={video_id}")
    if not resp or resp.status_code != 200:
        return {"error": "抖音API请求失败"}

    try:
        data = resp.json()
    except:
        return {"error": "响应格式错误"}

    detail = data.get("data", {}).get("aweme_detail")
    if not detail:
        return {"error": "未获取到视频数据"}

    author = detail.get("author", {})
    stats = detail.get("statistics", {})
    video = detail.get("video", {})

    # 如果有 douyin cookie，尝试用浏览器获取更完整数据
    if COOKIES.get("douyin"):
        try:
            browser_result = fetch_page(url, cookies=cookie_str_to_dict(COOKIES["douyin"]), wait_seconds=3)
            if "error" not in browser_result:
                result["browser_enhanced"] = True
                result["browser_title"] = browser_result.get("title", "")
        except:
            pass

    return {
        "title": detail.get("desc", ""),
        "author": {
            "nickname": author.get("nickname", ""),
            "douyin_id": author.get("unique_id", ""),
            "follower_count": author.get("follower_count", 0),
            "sec_uid": author.get("sec_uid", ""),
        },
        "stats": {
            "play_count": stats.get("play_count", 0),
            "digg_count": stats.get("digg_count", 0),
            "comment_count": stats.get("comment_count", 0),
            "collect_count": stats.get("collect_count", 0),
            "share_count": stats.get("share_count", 0),
        },
        "media": {
            "video_urls": video.get("play_addr", {}).get("url_list", []),
            "cover_urls": video.get("cover", {}).get("url_list", []),
            "duration": detail.get("duration", 0),
        },
        "music": {
            "title": detail.get("music", {}).get("title", ""),
            "author": detail.get("music", {}).get("author", ""),
        },
        "raw_text": detail.get("desc", ""),
        "raw_data": detail,
    }


def parse_douyin_user(sec_uid):
    if not sec_uid:
        return {"error": "缺少sec_uid"}
    resp = _req(f"{PARSER_API_URL}/api/douyin/web/handler_user_profile?sec_user_id={sec_uid}")
    if not resp or resp.status_code != 200:
        return {"error": "请求用户信息失败"}
    try:
        data = resp.json()
    except:
        return {"error": "响应格式错误"}
    user = data.get("data", {}).get("user", {})
    if not user:
        return {"error": "未找到用户信息"}
    return {
        "nickname": user.get("nickname", ""),
        "douyin_id": user.get("unique_id", ""),
        "sec_uid": user.get("sec_uid", ""),
        "signature": user.get("signature", ""),
        "follower_count": user.get("follower_count", 0),
        "following_count": user.get("following_count", 0),
        "total_favorited": user.get("total_favorited", 0),
        "aweme_count": user.get("aweme_count", 0),
        "raw_data": user,
    }
