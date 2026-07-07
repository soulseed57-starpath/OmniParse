"""
OmniParse - 统一内容解析服务
自动识别链接类型，走对应解析通道
"""

import os
import sys
import re
import json
import logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any

# 启动时检查配置
from config import check_config
if not check_config():
    sys.exit(1)

from parsers.douyin import parse_douyin_video, parse_douyin_user
from parsers.wechat import parse_wechat_article
from parsers.bilibili import parse_bilibili_video
from parsers.alibaba import parse as parse_alibaba

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omniparse")

app = FastAPI(
    title="OmniParse",
    description="统一内容解析服务 - 自动识别并解析抖音/公众号/B站/闲鱼",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseResult(BaseModel):
    success: bool
    platform: str = ""
    type: str = ""
    data: Any = None
    error: str = ""


def identify(url: str) -> Optional[tuple]:
    if not url:
        return None
    u = url.lower()
    if re.search(r'douyin\.(com|cn)', u):
        if re.search(r'/video/', u) or re.search(r'v\.douyin\.com', u):
            return ("douyin", "video")
        if re.search(r'/user/', u):
            return ("douyin", "user")
        return ("douyin", "video")
    if "mp.weixin.qq.com" in u:
        return ("wechat", "article")
    if re.search(r'(bilibili\.com|b23\.tv)', u):
        return ("bilibili", "video")
    if re.search(r'(goofish\.com|market\.m\.taobao\.com.*idle|ys\.alipay)', u):
        return ("xianyu", "item")
    if re.search(r'(taobao\.com|e\.tb\.cn)', u):
        return ("taobao", "item")
    return None


@app.get("/")
def root():
    return {
        "service": "OmniParse",
        "version": "1.0.0",
        "supported": [
            "抖音: douyin.com / v.douyin.com",
            "公众号: mp.weixin.qq.com",
            "B站: bilibili.com / b23.tv",
            "闲鱼: goofish.com",
        ],
    }


@app.get("/api/parse", response_model=ParseResult)
def parse_url(url: str = Query(...), verbose: bool = False):
    identified = identify(url)
    if not identified:
        return ParseResult(success=False, error="不支持的链接类型")

    platform, content_type = identified
    logger.info(f"解析: [{platform}/{content_type}] {url}")

    try:
        if platform == "douyin" and content_type == "video":
            data = parse_douyin_video(url)
        elif platform == "douyin" and content_type == "user":
            m = re.search(r'/user/([^/?]+)', url)
            data = parse_douyin_user(m.group(1)) if m else {"error": "无法解析用户链接"}
        elif platform == "wechat":
            data = parse_wechat_article(url)
        elif platform == "bilibili":
            data = parse_bilibili_video(url)
        elif platform == "xianyu":
            data = parse_alibaba(url)
        elif platform == "taobao":
            data = parse_alibaba(url)
        else:
            return ParseResult(success=False, error="不支持的解析类型")

        if "error" in data:
            # 检查是否需要 cookies
            err_msg = data["error"]
            if platform in ["taobao", "xianyu", "douyin"]:
                from config import COOKIES
                if not COOKIES.get(platform):
                    err_msg += f" | 💡 此平台需要登录才能完整解析，可在 config.yaml 配置 {platform} 的 cookies"
            return ParseResult(success=False, platform=platform, type=content_type, error=err_msg)
        if not verbose:
            for key in ["raw_data", "raw_text", "images"]:
                data.pop(key, None)
        return ParseResult(success=True, platform=platform, type=content_type, data=data)
    except Exception as e:
        return ParseResult(success=False, error=f"解析异常: {str(e)}")


@app.get("/api/identify")
def identify_url(url: str = Query(...)):
    result = identify(url)
    return {"platform": result[0] if result else None, "type": result[1] if result else None}


@app.get("/health")
def health():
    return {"status": "ok"}
