"""
Douyin collector.
"""
from __future__ import annotations

import asyncio
import json
import random
import re
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlencode, urlparse

import httpx

from app.core.config import settings
from app.models.schemas import NoteRecord
from app.services.douyin_sign import DouyinSigner


class DouyinCollector:
    """Douyin collector for videos and creator data."""

    def __init__(self, cookie: str, user_agent: Optional[str] = None, ms_token: Optional[str] = None):
        self.cookie = cookie
        self.user_agent = user_agent or settings.DEFAULT_USER_AGENT
        self.ms_token = ms_token or self._extract_cookie_value("msToken")
        self.webid = self._generate_webid()
        self._signer = DouyinSigner()
        self._host = "https://www.douyin.com"
        self._verify_fp = "verify_ma3hrt8n_q2q2HyYA_uLyO_4N6D_BLvX_E2LgoGmkA1BU"

    async def _random_delay(self, min_sec: float, max_sec: float) -> float:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
        return delay

    async def _get_smart_delay(self, index: int) -> float:
        if index < 5:
            return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_EARLY)
        if index < 10:
            return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_MIDDLE)
        return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_LATE)

    def _extract_cookie_value(self, key: str) -> str:
        cookie = SimpleCookie()
        cookie.load(self.cookie)
        morsel = cookie.get(key)
        return morsel.value if morsel else ""

    def _generate_webid(self) -> str:
        def _rand_fragment(value: Optional[int]) -> str:
            if value is not None:
                return str(value ^ (int(16 * random.random()) >> (value // 4)))
            template = f"{int(1e7)}-{int(1e3)}-{int(4e3)}-{int(8e3)}-{int(1e11)}"
            return template

        web_id = "".join(_rand_fragment(int(ch)) if ch in "018" else ch for ch in _rand_fragment(None))
        return web_id.replace("-", "")[:19]

    def _build_common_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "version_code": "190600",
            "version_name": "19.6.0",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "cookie_enabled": "true",
            "browser_language": "zh-CN",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "125.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "109.0",
            "os_name": "Mac OS",
            "os_version": "10.15.7",
            "cpu_core_num": "8",
            "device_memory": "8",
            "platform": "PC",
            "screen_width": "2560",
            "screen_height": "1440",
            "effective_type": "4g",
            "round_trip_time": "50",
            "webid": self.webid,
        }
        if self.ms_token:
            params["msToken"] = self.ms_token
        return params

    def _build_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.douyin.com",
            "Referer": referer or "https://www.douyin.com/",
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
        }
        return headers

    def _sign_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query_string = urlencode(params)
        a_bogus = self._signer.sign(query_string, self.user_agent)
        params["a_bogus"] = a_bogus
        return params

    async def _get(self, uri: str, params: Dict[str, Any], referer: Optional[str] = None, sign: bool = True) -> Dict[str, Any]:
        merged_params = params.copy()
        merged_params.update(self._build_common_params())

        if sign:
            merged_params = self._sign_params(merged_params)

        headers = self._build_headers(referer=referer)
        url = f"{self._host}{uri}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=merged_params, headers=headers)

        if response.status_code != 200:
            raise Exception(f"抖音接口请求失败: HTTP {response.status_code}")

        data = response.json()
        status_code = data.get("status_code")
        if status_code not in (None, 0):
            raise Exception(f"抖音接口返回异常: {data.get('status_msg', status_code)}")
        return data

    async def resolve_short_url(self, short_url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            try:
                response = await client.get(short_url)
            except Exception:
                return ""

        if response.status_code in {301, 302, 303, 307, 308}:
            return response.headers.get("Location", "")
        return ""

    def _parse_video_id_from_url(self, video_url: str) -> Tuple[str, bool]:
        video_url = video_url.strip()
        if video_url.isdigit():
            return video_url, False

        if "v.douyin.com" in video_url:
            return "", True

        params = parse_qs(urlparse(video_url).query)
        modal_id = params.get("modal_id", [""])[0]
        if modal_id:
            return modal_id, False

        match = re.search(r"/video/(\d+)", video_url)
        if match:
            return match.group(1), False

        return "", False

    async def resolve_video_id(self, video_url: str) -> str:
        aweme_id, needs_resolve = self._parse_video_id_from_url(video_url)
        if aweme_id:
            return aweme_id

        if needs_resolve:
            resolved = await self.resolve_short_url(video_url)
            if not resolved:
                raise ValueError("无法解析抖音短链接")
            aweme_id, _ = self._parse_video_id_from_url(resolved)
            if aweme_id:
                return aweme_id

        raise ValueError(f"无法从链接解析视频ID: {video_url}")

    def _extract_sec_user_id(self, profile_url: str) -> str:
        profile_url = profile_url.strip()
        if profile_url.startswith("MS4wLjAB") or (not profile_url.startswith("http") and "douyin.com" not in profile_url):
            return profile_url

        match = re.search(r"/user/([^/?]+)", profile_url)
        if match:
            return match.group(1)
        raise ValueError(f"无法从链接解析博主ID: {profile_url}")

    def _extract_cover_url(self, aweme_detail: Dict[str, Any]) -> str:
        video = aweme_detail.get("video") or {}
        cover = video.get("raw_cover") or video.get("origin_cover") or video.get("cover") or {}
        url_list = cover.get("url_list") or []
        if url_list:
            return url_list[-1]
        return ""

    def _extract_video_url(self, aweme_detail: Dict[str, Any]) -> str:
        video = aweme_detail.get("video") or {}
        for key in ("play_addr_h264", "play_addr_256", "play_addr", "download_addr"):
            url_list = (video.get(key) or {}).get("url_list") or []
            if url_list:
                return url_list[-1]
        return ""

    def _extract_image_urls(self, aweme_detail: Dict[str, Any]) -> List[str]:
        images = aweme_detail.get("images") or []
        urls: List[str] = []
        for image in images:
            url_list = image.get("url_list") or image.get("download_url_list") or []
            if url_list:
                urls.append(url_list[-1])
        return urls

    def _extract_tags(self, aweme_detail: Dict[str, Any]) -> List[str]:
        tags: List[str] = []
        text_extra = aweme_detail.get("text_extra") or []
        for item in text_extra:
            name = item.get("hashtag_name") or ""
            if name:
                tags.append(name)

        if not tags:
            desc = aweme_detail.get("desc", "") or ""
            matches = re.findall(r"#([^#\s]+)", desc)
            tags = [m.strip() for m in matches if m.strip()]

        seen = set()
        deduped: List[str] = []
        for tag in tags:
            if tag in seen:
                continue
            seen.add(tag)
            deduped.append(tag)
        return deduped

    async def fetch_video_detail(self, aweme_id: str) -> Dict[str, Any]:
        uri = "/aweme/v1/web/aweme/detail/"
        params = {"aweme_id": aweme_id}
        data = await self._get(uri, params, referer=f"https://www.douyin.com/video/{aweme_id}")
        aweme_detail = data.get("aweme_detail") or {}
        if not aweme_detail:
            raise Exception("未获取到视频详情")
        return aweme_detail

    async def fetch_user_profile(self, sec_user_id: str) -> Dict[str, Any]:
        uri = "/aweme/v1/web/user/profile/other/"
        params = {
            "sec_user_id": sec_user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
        }
        return await self._get(uri, params, referer=f"https://www.douyin.com/user/{sec_user_id}")

    async def fetch_user_posts(self, sec_user_id: str, max_notes: int) -> List[Dict[str, Any]]:
        uri = "/aweme/v1/web/aweme/post/"
        max_cursor = "0"
        has_more = True
        results: List[Dict[str, Any]] = []

        while has_more and len(results) < max_notes:
            params = {
                "sec_user_id": sec_user_id,
                "count": 18,
                "max_cursor": max_cursor,
                "locate_query": "false",
                "publish_video_strategy_type": 2,
                "verifyFp": self._verify_fp,
                "fp": self._verify_fp,
            }
            data = await self._get(uri, params, referer=f"https://www.douyin.com/user/{sec_user_id}")
            aweme_list = data.get("aweme_list") or []
            if aweme_list:
                for item in aweme_list:
                    results.append(item)
                    if len(results) >= max_notes:
                        break
            has_more = bool(data.get("has_more"))
            max_cursor = str(data.get("max_cursor") or "0")

            if has_more and len(results) < max_notes:
                await self._random_delay(0.4, 1.2)

        return results

    async def search_videos(self, keyword: str, max_notes: int, sort: str = "general") -> List[Dict[str, Any]]:
        uri = "/aweme/v1/web/general/search/single/"
        offset = 0
        search_id = ""
        results: List[Dict[str, Any]] = []
        sort_map = {
            "general": 0,
            "most_like": 1,
            "latest": 2,
            "hot_desc": 1,
            "time_desc": 2,
        }
        sort_value = sort_map.get(sort, 0)

        while len(results) < max_notes:
            remaining = max_notes - len(results)
            count = min(15, remaining)
            params = {
                "search_channel": "aweme_general",
                "enable_history": "1",
                "keyword": keyword,
                "search_source": "tab_search",
                "query_correct_type": "1",
                "is_filter_search": "0",
                "from_group_id": "7378810571505847586",
                "offset": offset,
                "count": count,
                "need_filter_settings": "1",
                "list_type": "multi",
                "search_id": search_id,
            }
            if sort_value != 0:
                params["filter_selected"] = json.dumps({"sort_type": str(sort_value), "publish_time": "0"})
                params["is_filter_search"] = 1

            referer = f"https://www.douyin.com/search/{quote(keyword)}?type=general"
            data = await self._get(uri, params, referer=referer, sign=False)

            items = data.get("data") or []
            if not items:
                break

            for item in items:
                aweme_info = item.get("aweme_info")
                if not aweme_info:
                    mix_items = (item.get("aweme_mix_info") or {}).get("mix_items") or []
                    aweme_info = mix_items[0] if mix_items else None
                if not isinstance(aweme_info, dict):
                    continue
                results.append(aweme_info)
                if len(results) >= max_notes:
                    break

            search_id = data.get("extra", {}).get("logid") or search_id
            offset += count

            if len(results) < max_notes:
                await self._random_delay(0.4, 1.2)

        return results

    async def _ensure_aweme_detail(self, aweme_item: Dict[str, Any]) -> Dict[str, Any]:
        if aweme_item.get("statistics") and (aweme_item.get("video") or aweme_item.get("images")):
            return aweme_item
        aweme_id = aweme_item.get("aweme_id")
        if not aweme_id:
            return aweme_item
        return await self.fetch_video_detail(aweme_id)

    def process_aweme_detail(self, aweme_detail: Dict[str, Any]) -> NoteRecord:
        aweme_id = aweme_detail.get("aweme_id", "")
        desc = aweme_detail.get("desc") or ""
        statistics = aweme_detail.get("statistics") or {}
        author = aweme_detail.get("author") or {}

        image_urls = self._extract_image_urls(aweme_detail)
        image_text = "\n".join([url for url in image_urls if url])

        cover_url = self._extract_cover_url(aweme_detail)
        if not cover_url and image_urls:
            cover_url = image_urls[0]

        video_url = self._extract_video_url(aweme_detail)
        note_type = "normal" if image_urls else "video"
        tags = self._extract_tags(aweme_detail)

        user_nickname = author.get("nickname") or ""
        sec_uid = author.get("sec_uid") or ""
        user_avatar = (
            (author.get("avatar_medium") or {}).get("url_list")
            or (author.get("avatar_thumb") or {}).get("url_list")
            or []
        )
        user_avatar_url = user_avatar[0] if user_avatar else ""
        user_home_page = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""

        return NoteRecord(fields={
            "图片链接": image_text,
            "笔记封面图链接": cover_url,
            "笔记标题": desc,
            "笔记内容": desc,
            "笔记类型": note_type,
            "笔记链接": f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
            "笔记标签": tags,
            "账号名称": user_nickname,
            "主页链接": user_home_page,
            "头像链接": user_avatar_url,
            "分享数": int(statistics.get("share_count", 0) or 0),
            "点赞数": int(statistics.get("digg_count", 0) or 0),
            "收藏数": int(statistics.get("collect_count", 0) or 0),
            "评论数": int(statistics.get("comment_count", 0) or 0),
            "视频链接": video_url,
            "发布时间": aweme_detail.get("create_time", 0) or 0,
        })

    def process_profile_info(self, profile_data: Dict[str, Any], sec_user_id: str) -> NoteRecord:
        user = profile_data.get("user") or {}
        gender_map = {0: "未知", 1: "男", 2: "女"}
        avatar_info = user.get("avatar_300x300") or user.get("avatar_medium") or user.get("avatar_thumb") or {}
        avatar_url_list = avatar_info.get("url_list") or []
        avatar_url = avatar_url_list[0] if avatar_url_list else ""

        dy_id = user.get("unique_id") or user.get("short_id") or user.get("uid") or ""

        return NoteRecord(fields={
            "博主ID": sec_user_id or user.get("sec_uid") or user.get("uid") or "",
            "博主昵称": user.get("nickname") or "",
            "小红书号": dy_id,
            "个人简介": user.get("signature") or "",
            "性别": gender_map.get(user.get("gender"), "未知"),
            "IP属地": user.get("ip_location") or "",
            "头像链接": avatar_url,
            "关注数": user.get("following_count") or 0,
            "粉丝数": user.get("max_follower_count") or user.get("follower_count") or 0,
            "获赞与收藏": user.get("total_favorited") or 0,
            "主页链接": f"https://www.douyin.com/user/{sec_user_id}" if sec_user_id else "",
        })

    async def collect_single_video(self, video_url: str) -> NoteRecord:
        aweme_id = await self.resolve_video_id(video_url)
        detail = await self.fetch_video_detail(aweme_id)
        return self.process_aweme_detail(detail)

    async def collect_creator_profile(self, profile_url: str) -> NoteRecord:
        sec_user_id = self._extract_sec_user_id(profile_url)
        profile_data = await self.fetch_user_profile(sec_user_id)
        return self.process_profile_info(profile_data, sec_user_id)

    async def collect_creator_videos(
        self,
        profile_url: str,
        max_notes: int = 20,
    ) -> Tuple[List[NoteRecord], int, int, List[str]]:
        sec_user_id = self._extract_sec_user_id(profile_url)
        await self._random_delay(*settings.DELAY_BEFORE_HOME)
        aweme_list = await self.fetch_user_posts(sec_user_id, max_notes)

        if not aweme_list:
            return [], 0, 0, []

        records: List[NoteRecord] = []
        failed_ids: List[str] = []
        success_count = 0
        fail_count = 0

        for index, aweme_item in enumerate(aweme_list):
            try:
                aweme_detail = await self._ensure_aweme_detail(aweme_item)
                record = self.process_aweme_detail(aweme_detail)
                records.append(record)
                success_count += 1
            except Exception as exc:
                aweme_id = aweme_item.get("aweme_id") or ""
                failed_ids.append(aweme_id)
                fail_count += 1
                print(f"采集抖音视频 {aweme_id} 失败: {exc}")

            if index < len(aweme_list) - 1:
                await self._get_smart_delay(index)

        return records, success_count, fail_count, failed_ids

    async def collect_videos_by_keyword(
        self,
        keyword: str,
        max_notes: int = 20,
        sort: str = "general",
    ) -> Tuple[List[NoteRecord], int, int, List[str]]:
        aweme_list = await self.search_videos(keyword, max_notes, sort)

        if not aweme_list:
            return [], 0, 0, []

        records: List[NoteRecord] = []
        failed_ids: List[str] = []
        success_count = 0
        fail_count = 0

        for index, aweme_item in enumerate(aweme_list):
            try:
                aweme_detail = await self._ensure_aweme_detail(aweme_item)
                record = self.process_aweme_detail(aweme_detail)
                records.append(record)
                success_count += 1
            except Exception as exc:
                aweme_id = aweme_item.get("aweme_id") or ""
                failed_ids.append(aweme_id)
                fail_count += 1
                print(f"采集抖音视频 {aweme_id} 失败: {exc}")

            if index < len(aweme_list) - 1:
                await self._get_smart_delay(index)

        return records, success_count, fail_count, failed_ids
