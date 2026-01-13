"""
小红书采集模块
负责采集博主主页笔记数据
"""
import asyncio
import random
import re
import json
from urllib.parse import urlparse, parse_qs, quote, urlencode
from typing import List, Dict, Any, Optional, Tuple

import httpx

from app.core.config import settings
from app.models.schemas import NoteInfo, NoteRecord
from app.services.xhs_sign import generate_sign_headers, XhsSign


class XhsCollector:
    """小红书采集器"""
    
    def __init__(self, cookie: str, user_agent: Optional[str] = None):
        self.cookie = cookie
        self.user_agent = user_agent or settings.DEFAULT_USER_AGENT
    
    async def _random_delay(self, min_sec: float, max_sec: float) -> float:
        """随机延迟"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
        return delay
    
    async def _get_smart_delay(self, index: int) -> float:
        """智能延迟（根据笔记序号）"""
        if index < 5:
            return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_EARLY)
        elif index < 10:
            return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_MIDDLE)
        else:
            return await self._random_delay(*settings.DELAY_BETWEEN_NOTES_LATE)

    def _parse_initial_state(self, html_content: str) -> Dict[str, Any]:
        """解析页面中的 __INITIAL_STATE__"""
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+\})\s*</script>', html_content, re.DOTALL)

        if not state_match:
            state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html_content, re.DOTALL)

        if not state_match:
            raise Exception("未在 HTML 中找到 __INITIAL_STATE__，Cookie 可能已失效")

        try:
            json_str = state_match.group(1)
            json_str = re.sub(r'\bundefined\b', 'null', json_str)
            json_str = re.sub(r'\bNaN\b', 'null', json_str)
            json_str = re.sub(r'\bInfinity\b', 'null', json_str)

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"解析 __INITIAL_STATE__ 失败: {e}")

    def _extract_user_id_from_url(self, profile_url: str) -> str:
        """从主页 URL 中提取用户 ID"""
        # https://www.xiaohongshu.com/user/profile/688428ec000000001b0238a9?...
        match = re.search(r'/user/profile/([a-f0-9]+)', profile_url)
        if match:
            return match.group(1)
        raise ValueError(f"无法从 URL 中提取用户 ID: {profile_url}")

    def _extract_note_id_from_url(self, note_url: str) -> str:
        """从笔记 URL 中提取笔记 ID"""
        note_url = note_url.strip()
        for pattern in (r'/explore/([a-zA-Z0-9]+)', r'/discovery/item/([a-zA-Z0-9]+)'):
            match = re.search(pattern, note_url)
            if match:
                return match.group(1)
        raise ValueError(f"无法从 URL 中提取笔记 ID: {note_url}")

    def _extract_xsec_token_from_url(self, note_url: str) -> str:
        """从笔记 URL 中提取 xsec_token"""
        query = urlparse(note_url).query
        token = parse_qs(query).get("xsec_token", [""])[0]
        return token or ""

    def _extract_xsec_token_from_html(self, html_content: str, note_id: str = "") -> str:
        """从笔记详情页 HTML 中提取 xsec_token"""
        patterns = []
        if note_id:
            patterns.extend([
                rf'"note_id"\s*:\s*"{note_id}".+?"xsec_token"\s*:\s*"([^"]+)"',
                rf'"noteId"\s*:\s*"{note_id}".+?"xsecToken"\s*:\s*"([^"]+)"',
            ])
        patterns.extend([
            r'"xsec_token"\s*:\s*"([^"]+)"',
            r'"xsecToken"\s*:\s*"([^"]+)"',
        ])
        for pattern in patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                return match.group(1)
        return ""

    def _extract_note_info_from_html(self, html_content: str, note_id: str) -> Dict[str, str]:
        """从笔记详情页 HTML 中提取用户与笔记基础信息"""
        initial_state = self._parse_initial_state(html_content)
        note_state = initial_state.get("note") if isinstance(initial_state, dict) else {}
        note_map = note_state.get("noteDetailMap") if isinstance(note_state, dict) else {}

        if not isinstance(note_map, dict) or not note_map:
            return {}

        note_entry = note_map.get(note_id) or next(iter(note_map.values()), {})
        if not isinstance(note_entry, dict):
            return {}

        note_detail = note_entry.get("note") or note_entry.get("noteCard") or note_entry
        if not isinstance(note_detail, dict):
            return {}

        user = note_detail.get("user") or {}
        user_id = user.get("userId") or user.get("user_id") or ""
        user_home_page = f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else ""

        return {
            "displayTitle": note_detail.get("display_title") or note_detail.get("displayTitle") or note_detail.get("title", ""),
            "type": note_detail.get("type", ""),
            "userNickname": user.get("nickname") or user.get("nickName") or "",
            "userId": user_id,
            "userAvatar": user.get("avatar") or "",
            "userHomePage": user_home_page
        }

    def _build_search_url(self, keyword: str) -> str:
        """构造搜索 URL"""
        params = {
            "keyword": keyword,
            "source": "web_explore_feed",
        }
        return f"https://www.xiaohongshu.com/search_result?{urlencode(params)}"

    def _parse_interaction_count(self, interactions: List[Dict[str, Any]], target_type: str) -> int:
        """解析博主互动数据中的计数值"""
        for item in interactions:
            if item.get("type") != target_type:
                continue
            count = item.get("count", 0)
            if isinstance(count, (int, float)):
                return int(count)
            if isinstance(count, str):
                num_str = count.replace(",", "").strip()
                if "万" in num_str:
                    try:
                        return round(float(num_str.replace("万", "")) * 10000)
                    except ValueError:
                        return 0
                try:
                    return int(float(num_str))
                except ValueError:
                    return 0
            return 0
        return 0

    def _extract_image_url(self, image_info: Dict[str, Any]) -> str:
        """提取图片链接"""
        if not isinstance(image_info, dict):
            return ""
        for key in ("url_default", "url_pre", "url", "urlDefault", "urlPre"):
            url = image_info.get(key)
            if url:
                return url
        info_list = image_info.get("infoList") or []
        if isinstance(info_list, list):
            for item in info_list:
                url = self._extract_image_url(item) if isinstance(item, dict) else ""
                if url:
                    return url
        return ""

    def _find_first_url(self, value: Any) -> str:
        """在嵌套数据中查找第一个可用 URL"""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("http"):
                return text
            if text.startswith("//"):
                return f"https:{text}"
            if text.endswith((".mp4", ".mov", ".m3u8")):
                return f"https://sns-video-qc.xhscdn.com/{text.lstrip('/')}"
            return ""
        if isinstance(value, list):
            for item in value:
                url = self._find_first_url(item)
                if url:
                    return url
            return ""
        if isinstance(value, dict):
            priority_keys = (
                "origin_video_key",
                "originVideoKey",
                "url",
                "url_default",
                "url_pre",
                "urlPre",
                "download_url",
                "origin_url",
                "stream_url",
            )
            for key in priority_keys:
                if key in value:
                    url = self._find_first_url(value.get(key))
                    if url:
                        return url
            for sub_value in value.values():
                url = self._find_first_url(sub_value)
                if url:
                    return url
        return ""

    def _extract_video_url(self, video_info: Dict[str, Any]) -> str:
        """提取视频链接"""
        if not isinstance(video_info, dict):
            return ""
        return self._find_first_url(video_info)

    async def fetch_notes_via_api(self, profile_url: str, max_notes: int = 20) -> List[NoteInfo]:
        """
        通过 API 获取博主笔记列表（推荐方式）
        
        Args:
            profile_url: 博主主页链接
            max_notes: 最大笔记数量
            
        Returns:
            笔记信息列表
        """
        user_id = self._extract_user_id_from_url(profile_url)
        
        # 请求前延迟
        await self._random_delay(*settings.DELAY_BEFORE_HOME)
        
        signer = XhsSign()
        api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted"
        params = {
            "num": str(min(max_notes, 30)),
            "cursor": "",
            "user_id": user_id,
            "image_formats": "jpg,webp,avif"
        }
        
        sign_headers = signer.sign_headers_get(api_url, self.cookie, params=params)
        
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cookie": self.cookie,
            "origin": "https://www.xiaohongshu.com",
            "referer": f"https://www.xiaohongshu.com/user/profile/{user_id}",
            "user-agent": self.user_agent,
        }
        headers.update(sign_headers)
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{api_url}?{query}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(full_url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"请求笔记列表 API 失败: HTTP {response.status_code}")
            
            data = response.json()
            
            if data.get("code") == -100:
                raise Exception("Cookie 已失效，请重新获取")
            
            if data.get("code") != 0:
                raise Exception(f"API 返回错误: {data.get('msg', '未知错误')}")
            
            notes_data = data.get("data", {}).get("notes", [])
            
            if not notes_data:
                raise Exception("该博主暂无笔记数据")
            
            # 构建用户主页链接
            user_home_page = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            
            # 提取笔记信息
            note_list = []
            for note in notes_data[:max_notes]:
                note_info = NoteInfo(
                    noteId=note.get("note_id", ""),
                    xsecToken=note.get("xsec_token", ""),
                    displayTitle=note.get("display_title", ""),
                    type=note.get("type", ""),
                    userNickname=note.get("user", {}).get("nickname", ""),
                    userId=note.get("user", {}).get("user_id", user_id),
                    userAvatar=note.get("user", {}).get("avatar", ""),
                    userHomePage=user_home_page
                )
                if note_info.noteId and note_info.xsecToken:
                    note_list.append(note_info)
            
            return note_list

    def _build_note_info_from_search_item(self, item: Dict[str, Any]) -> Optional[NoteInfo]:
        """从搜索结果中构造 NoteInfo"""
        if not isinstance(item, dict):
            return None

        note_card = (
            item.get("note_card")
            or item.get("noteCard")
            or item.get("note_info")
            or item.get("noteInfo")
            or item.get("note")
            or {}
        )
        if not isinstance(note_card, dict):
            note_card = {}

        note_id = (
            note_card.get("note_id")
            or note_card.get("noteId")
            or item.get("note_id")
            or item.get("noteId")
            or item.get("id")
            or ""
        )
        if not note_id:
            return None

        xsec_token = (
            note_card.get("xsec_token")
            or note_card.get("xsecToken")
            or item.get("xsec_token")
            or item.get("xsecToken")
            or ""
        )

        display_title = (
            note_card.get("display_title")
            or note_card.get("displayTitle")
            or note_card.get("title")
            or ""
        )

        note_type = note_card.get("type", "")

        user = (
            note_card.get("user")
            or note_card.get("user_info")
            or note_card.get("userInfo")
            or item.get("user")
            or {}
        )
        if not isinstance(user, dict):
            user = {}

        user_nickname = user.get("nickname") or user.get("nick_name") or user.get("nickName") or ""
        user_id = user.get("user_id") or user.get("userId") or ""
        user_avatar = user.get("avatar") or user.get("avatar_url") or user.get("image") or ""
        user_home_page = f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else ""

        return NoteInfo(
            noteId=note_id,
            xsecToken=xsec_token,
            displayTitle=display_title,
            type=note_type,
            userNickname=user_nickname,
            userId=user_id,
            userAvatar=user_avatar,
            userHomePage=user_home_page
        )

    async def search_notes_via_api(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "general",
        note_type: int = 0,
        search_id: str = ""
    ) -> Tuple[List[NoteInfo], bool, str]:
        """通过关键词搜索获取笔记列表"""
        keyword = keyword.strip()
        page_size = max(1, min(page_size, 20))

        payload: Dict[str, Any] = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "note_type": note_type,
            "image_formats": ["jpg", "webp", "avif"],
        }
        if search_id:
            payload["search_id"] = search_id

        api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
        signer = XhsSign()
        sign_headers = signer.sign_headers_post(api_url, self.cookie, payload=payload)

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}",
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
        }
        headers.update(sign_headers)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

            if response.status_code != 200:
                raise Exception(f"搜索请求失败: HTTP {response.status_code}")

            data = response.json()

            if data.get("code") == -100:
                raise Exception("Cookie 已失效，请重新获取")

            if data.get("code") != 0:
                raise Exception(f"搜索接口返回错误: {data.get('msg', '未知错误')}")

            result_data = data.get("data", {})
            items = result_data.get("items") or result_data.get("notes") or []

            note_list: List[NoteInfo] = []
            for item in items:
                note_info = self._build_note_info_from_search_item(item)
                if note_info:
                    note_list.append(note_info)

            has_more = bool(result_data.get("has_more") or result_data.get("hasMore"))
            new_search_id = result_data.get("search_id") or result_data.get("searchId") or search_id

            return note_list, has_more, new_search_id
    
    async def fetch_homepage_html(self, profile_url: str) -> Tuple[str, str]:
        """
        获取博主主页 HTML
        
        Args:
            profile_url: 博主主页链接
            
        Returns:
            (html_content, clean_url)
        """
        # 清理 URL，但保留 xsec_token 参数
        profile_url = profile_url.strip()
        # 提取基础 URL（不含参数）用于后续笔记构建
        clean_url = profile_url.split("?")[0].strip()
        # 请求时使用完整 URL（包含 xsec_token）
        request_url = profile_url
        
        # 请求前延迟
        await self._random_delay(*settings.DELAY_BEFORE_HOME)
        
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "cookie": self.cookie,
            "referer": "https://www.xiaohongshu.com/"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request_url, headers=headers, follow_redirects=True)
            
            if response.status_code != 200:
                raise Exception(f"请求主页失败: HTTP {response.status_code}")
            
            return response.text, clean_url

    async def fetch_search_html(self, keyword: str) -> str:
        """获取搜索结果页 HTML"""
        keyword = keyword.strip()
        search_url = self._build_search_url(keyword)

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "cookie": self.cookie,
            "referer": "https://www.xiaohongshu.com/"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(search_url, headers=headers, follow_redirects=True)

            if response.status_code != 200:
                raise Exception(f"请求搜索页失败: HTTP {response.status_code}")

            return response.text

    async def fetch_note_html(self, note_url: str) -> str:
        """获取笔记详情页 HTML"""
        note_url = note_url.strip()

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "cookie": self.cookie,
            "referer": "https://www.xiaohongshu.com/"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(note_url, headers=headers, follow_redirects=True)

            if response.status_code != 200:
                raise Exception(f"请求笔记详情页失败: HTTP {response.status_code}")

            return response.text

    async def build_note_info_from_url(self, note_url: str) -> NoteInfo:
        """从笔记链接构造 NoteInfo"""
        note_id = self._extract_note_id_from_url(note_url)
        xsec_token = self._extract_xsec_token_from_url(note_url)
        html_content = None

        if not xsec_token:
            html_content = await self.fetch_note_html(note_url)
            xsec_token = self._extract_xsec_token_from_html(html_content, note_id)
        else:
            try:
                html_content = await self.fetch_note_html(note_url)
            except Exception:
                html_content = None

        if not xsec_token:
            raise ValueError("笔记链接缺少 xsec_token，请提供完整链接")

        extra_info: Dict[str, str] = {}
        if html_content:
            try:
                extra_info = self._extract_note_info_from_html(html_content, note_id)
            except Exception:
                extra_info = {}
        return NoteInfo(noteId=note_id, xsecToken=xsec_token, **extra_info)

    async def _ensure_note_xsec_token(self, note_info: NoteInfo) -> NoteInfo:
        """确保 NoteInfo 包含 xsec_token"""
        if note_info.xsecToken:
            return note_info

        note_url = f"https://www.xiaohongshu.com/explore/{note_info.noteId}"
        fallback_info = await self.build_note_info_from_url(note_url)
        updates = {"xsecToken": fallback_info.xsecToken}
        for field in ("displayTitle", "type", "userNickname", "userId", "userAvatar", "userHomePage"):
            value = getattr(fallback_info, field, "")
            if value:
                updates[field] = value
        return note_info.copy(update=updates)

    def extract_note_list(self, html_content: str, max_notes: int = 20) -> Tuple[List[NoteInfo], str]:
        """
        从主页 HTML 中提取笔记列表
        
        Args:
            html_content: 主页 HTML 内容
            max_notes: 最大笔记数量
            
        Returns:
            (笔记列表, 用户主页链接)
        """
        # 提取 __INITIAL_STATE__（支持多种格式）
        # 格式1: window.__INITIAL_STATE__={...}</script>
        # 格式2: window.__INITIAL_STATE__ = {...};
        initial_state = self._parse_initial_state(html_content)
        
        # 提取笔记数据
        notes_data = initial_state.get("user", {}).get("userPageData", {}).get("notes", [])
        
        if not notes_data or not isinstance(notes_data, list):
            raise Exception("未找到笔记数据")
        
        first_notes_array = notes_data[0] if notes_data else []
        
        if not isinstance(first_notes_array, list) or len(first_notes_array) == 0:
            return [], ""
        
        # 提取用户信息
        first_note = first_notes_array[0].get("noteCard", {}) if first_notes_array else {}
        user_info = first_note.get("user", {})
        user_id = user_info.get("userId", "")
        user_nickname = user_info.get("nickname", "") or user_info.get("nickName", "")
        user_avatar = user_info.get("avatar", "")
        user_home_page = f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else ""
        
        # 提取笔记列表
        note_list: List[NoteInfo] = []
        for note_item in first_notes_array:
            note_card = note_item.get("noteCard", {})
            note_id = note_card.get("noteId", "")
            xsec_token = note_card.get("xsecToken", "")
            
            if note_id and xsec_token:
                note_list.append(NoteInfo(
                    noteId=note_id,
                    xsecToken=xsec_token,
                    displayTitle=note_card.get("displayTitle", ""),
                    type=note_card.get("type", ""),
                    userNickname=user_nickname,
                    userId=user_id,
                    userAvatar=user_avatar,
                    userHomePage=user_home_page
                ))
        
        # 限制数量
        return note_list[:max_notes], user_home_page

    def extract_search_notes(self, html_content: str) -> List[NoteInfo]:
        """从搜索页 HTML 中提取笔记列表"""
        initial_state = self._parse_initial_state(html_content)
        search_data = initial_state.get("search", {}) if isinstance(initial_state, dict) else {}
        feeds = search_data.get("feeds") or {}

        feeds_value: Any = []
        if isinstance(feeds, list):
            feeds_value = feeds
        elif isinstance(feeds, dict):
            feeds_value = feeds.get("value") or feeds.get("_value") or feeds.get("items") or feeds.get("list") or []

        if not isinstance(feeds_value, list):
            return []

        note_list: List[NoteInfo] = []
        for item in feeds_value:
            note_info = self._build_note_info_from_search_item(item)
            if note_info:
                note_list.append(note_info)

        return note_list

    async def search_notes_via_html(self, keyword: str, max_notes: int = 20) -> List[NoteInfo]:
        """通过搜索页 HTML 获取笔记列表"""
        html_content = await self.fetch_search_html(keyword)
        notes = self.extract_search_notes(html_content)
        return notes[:max_notes]

    def extract_user_profile(self, html_content: str, profile_url: str) -> NoteRecord:
        """从主页 HTML 中提取博主信息"""
        initial_state = self._parse_initial_state(html_content)
        user_page_data = initial_state.get("user", {}).get("userPageData")

        if not user_page_data:
            raise Exception("未找到 userPageData 数据")

        result = user_page_data.get("result")
        if result and not result.get("success", True):
            raise Exception(f"获取博主信息失败: {result.get('message', '未知错误')}")

        basic_info = user_page_data.get("basicInfo", {})
        interactions = user_page_data.get("interactions", [])
        tags = user_page_data.get("tags", [])

        if not basic_info.get("nickname"):
            raise Exception("博主不存在或已注销")

        try:
            user_id = self._extract_user_id_from_url(profile_url)
        except ValueError:
            user_id = basic_info.get("userId") or basic_info.get("user_id") or ""

        tags_text = ""
        if isinstance(tags, list):
            tag_names = [
                tag.get("name", "")
                for tag in tags
                if isinstance(tag, dict) and tag.get("name")
            ]
            tags_text = ", ".join(tag_names)

        follows_count = self._parse_interaction_count(interactions, "follows")
        fans_count = self._parse_interaction_count(interactions, "fans")
        interaction_count = self._parse_interaction_count(interactions, "interaction")

        gender_map = {
            0: "未知",
            1: "男",
            2: "女",
        }
        gender = gender_map.get(basic_info.get("gender"), "未知")

        avatar = basic_info.get("imageb") or basic_info.get("images") or basic_info.get("image") or ""
        if isinstance(avatar, list):
            avatar = avatar[0] if avatar else ""
        if isinstance(avatar, dict):
            avatar = (
                avatar.get("url")
                or avatar.get("urlDefault")
                or avatar.get("url_pre")
                or avatar.get("urlPre")
                or ""
            )
        if avatar is None:
            avatar = ""
        if not isinstance(avatar, str):
            avatar = str(avatar)

        return NoteRecord(fields={
            "博主ID": user_id,
            "博主昵称": basic_info.get("nickname", ""),
            "小红书号": basic_info.get("redId", ""),
            "个人简介": basic_info.get("desc", ""),
            "性别": gender,
            "IP属地": basic_info.get("ipLocation", ""),
            "头像链接": avatar or "",
            "关注数": follows_count,
            "粉丝数": fans_count,
            "获赞与收藏": interaction_count,
            "主页链接": f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else "",
            "标签": tags_text
        })

    async def fetch_notes_by_keyword(
        self,
        keyword: str,
        max_notes: int = 20,
        sort: str = "general",
        note_type: int = 0
    ) -> List[NoteInfo]:
        """根据关键词分页获取笔记列表"""
        keyword = keyword.strip()
        notes: List[NoteInfo] = []
        seen_ids = set()
        search_id = ""
        page = 1

        while len(notes) < max_notes:
            remaining = max_notes - len(notes)
            page_size = min(20, remaining)

            try:
                page_notes, has_more, new_search_id = await self.search_notes_via_api(
                    keyword=keyword,
                    page=page,
                    page_size=page_size,
                    sort=sort,
                    note_type=note_type,
                    search_id=search_id
                )
            except Exception:
                if page == 1:
                    return await self.search_notes_via_html(keyword, max_notes)
                raise

            if not page_notes:
                break

            for note_info in page_notes:
                if note_info.noteId in seen_ids:
                    continue
                seen_ids.add(note_info.noteId)
                notes.append(note_info)
                if len(notes) >= max_notes:
                    break

            if not has_more:
                break

            search_id = new_search_id or search_id
            page += 1

        return notes
    
    async def fetch_note_detail(self, note_info: NoteInfo) -> Optional[Dict[str, Any]]:
        """
        获取笔记详情
        
        Args:
            note_info: 笔记信息
            
        Returns:
            feed API 响应数据
        """
        api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/feed"
        
        payload = {
            "source_note_id": note_info.noteId,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": "1"},
            "xsec_source": "pc_user",
            "xsec_token": note_info.xsecToken,
        }
        
        # 使用新的签名方式（包含 trace ID）
        signer = XhsSign()
        sign_headers = signer.sign_headers_post(api_url, self.cookie, payload=payload)
        
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": f"https://www.xiaohongshu.com/explore/{note_info.noteId}",
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
        }
        headers.update(sign_headers)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            
            if response.status_code == 406:
                raise Exception(f"签名验证失败 (406)")
            
            if response.status_code != 200:
                raise Exception(f"feed 请求失败: HTTP {response.status_code}")
            
            data = response.json()
            
            if data.get("code") == -100:
                raise Exception("Cookie 已失效，请重新获取")
            
            if data.get("code") != 0:
                raise Exception(f"feed 返回异常: {data.get('msg', data.get('code', 'unknown'))}")
            
            return data
    
    def process_note_detail(self, feed_data: Dict[str, Any], note_info: NoteInfo) -> NoteRecord:
        """
        处理笔记详情，转换为飞书表格记录格式
        
        Args:
            feed_data: feed API 响应数据
            note_info: 笔记基础信息
            
        Returns:
            飞书表格记录
        """
        items = feed_data.get("data", {}).get("items", [])
        
        if not items:
            raise Exception("feed 响应中没有找到笔记数据")
        
        note_item = items[0]
        note_card = note_item.get("note_card", {})
        
        user = note_card.get("user", {})
        interact_info = note_card.get("interact_info", {})
        image_list = note_card.get("image_list", [])
        tag_list = note_card.get("tag_list", [])
        video = note_card.get("video", {})
        
        # 图片链接（多张用换行分隔）
        image_text = "\n".join(
            img.get("url_default") or img.get("url_pre") or img.get("url", "")
            for img in image_list
            if img.get("url_default") or img.get("url_pre") or img.get("url")
        )
        
        # 标签数组（仅提取话题标签）
        tags_array = [
            tag.get("name", "")
            for tag in tag_list
            if tag.get("type") == "topic" and tag.get("name")
        ]
        
        # 视频链接
        video_url = self._extract_video_url(video)
        
        # 互动数据
        liked_count = int(interact_info.get("liked_count", 0) or 0)
        collected_count = int(interact_info.get("collected_count", 0) or 0)
        comment_count = int(interact_info.get("comment_count", 0) or 0)
        share_count = int(interact_info.get("share_count", 0) or 0)
        
        # 发布时间
        publish_time = note_card.get("time", 0)
        
        # 笔记链接
        note_id_for_url = note_card.get("note_id", note_info.noteId)
        xsec_token_for_url = note_card.get("xsec_token", note_info.xsecToken)
        note_url = f"https://www.xiaohongshu.com/explore/{note_id_for_url}?xsec_token={xsec_token_for_url}&xsec_source=pc_user"
        
        # 用户信息（优先使用详情中的，回退到列表中的）
        user_nickname = (
            user.get("nickname")
            or user.get("nickName")
            or user.get("nick_name")
            or note_info.userNickname
        )
        user_id = user.get("user_id") or user.get("userId") or note_info.userId
        user_avatar = (
            user.get("avatar")
            or user.get("avatar_url")
            or user.get("avatarUrl")
            or note_info.userAvatar
        )
        user_home_page = note_info.userHomePage or (f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else "")
        
        cover_url = self._extract_image_url(note_card.get("cover", {}))
        if not cover_url and image_list:
            cover_url = self._extract_image_url(image_list[0])

        return NoteRecord(fields={
            "图片链接": image_text,
            "笔记封面图链接": cover_url,
            "笔记标题": note_card.get("title") or note_card.get("display_title", ""),
            "笔记内容": note_card.get("desc", ""),
            "笔记类型": note_card.get("type", ""),
            "笔记链接": note_url,
            "笔记标签": tags_array,
            "账号名称": user_nickname,
            "主页链接": user_home_page,
            "头像链接": user_avatar,
            "分享数": share_count,
            "点赞数": liked_count,
            "收藏数": collected_count,
            "评论数": comment_count,
            "视频链接": video_url,
            "发布时间": publish_time
        })
    
    async def collect_all_notes(self, profile_url: str, max_notes: int = 20) -> Tuple[List[NoteRecord], int, int, List[str]]:
        """
        采集博主所有笔记
        
        Args:
            profile_url: 博主主页链接
            max_notes: 最大采集数量
            
        Returns:
            (记录列表, 成功数量, 失败数量, 失败的笔记ID列表)
        """
        # 1. 通过 API 获取笔记列表（推荐方式，可获取 noteId）
        note_list = await self.fetch_notes_via_api(profile_url, max_notes)
        
        if not note_list:
            return [], 0, 0, []
        
        # 3. 循环采集每条笔记详情
        records: List[NoteRecord] = []
        failed_note_ids: List[str] = []
        success_count = 0
        fail_count = 0
        
        for index, note_info in enumerate(note_list):
            try:
                # 获取笔记详情
                feed_data = await self.fetch_note_detail(note_info)
                
                if feed_data:
                    # 处理数据
                    record = self.process_note_detail(feed_data, note_info)
                    records.append(record)
                    success_count += 1
                else:
                    failed_note_ids.append(note_info.noteId)
                    fail_count += 1
                    
            except Exception as e:
                failed_note_ids.append(note_info.noteId)
                fail_count += 1
                print(f"采集笔记 {note_info.noteId} 失败: {e}")
            
            # 智能延迟（非最后一条）
            if index < len(note_list) - 1:
                await self._get_smart_delay(index)
        
        return records, success_count, fail_count, failed_note_ids

    async def collect_notes_by_keyword(
        self,
        keyword: str,
        max_notes: int = 20,
        sort: str = "general",
        note_type: int = 0
    ) -> Tuple[List[NoteRecord], int, int, List[str]]:
        """根据关键词采集笔记详情"""
        note_list = await self.fetch_notes_by_keyword(keyword, max_notes, sort, note_type)

        if not note_list:
            return [], 0, 0, []

        records: List[NoteRecord] = []
        failed_note_ids: List[str] = []
        success_count = 0
        fail_count = 0

        for index, note_info in enumerate(note_list):
            try:
                note_info = await self._ensure_note_xsec_token(note_info)
                feed_data = await self.fetch_note_detail(note_info)

                if feed_data:
                    record = self.process_note_detail(feed_data, note_info)
                    records.append(record)
                    success_count += 1
                else:
                    failed_note_ids.append(note_info.noteId)
                    fail_count += 1
            except Exception as e:
                failed_note_ids.append(note_info.noteId)
                fail_count += 1
                print(f"采集笔记 {note_info.noteId} 失败: {e}")

            if index < len(note_list) - 1:
                await self._get_smart_delay(index)

        return records, success_count, fail_count, failed_note_ids


def parse_feishu_table_url(url: str) -> Tuple[str, str]:
    """
    解析飞书表格链接，提取 app_token 和 table_id
    
    Args:
        url: 飞书表格链接
        
    Returns:
        (app_token, table_id)
    """
    url = url.strip()
    
    # 提取 app_token: /base/{app_token}
    app_token_match = re.search(r'/base/([a-zA-Z0-9]+)', url)
    app_token = app_token_match.group(1) if app_token_match else ""
    
    # 提取 table_id: ?table=tblxxxx
    table_id_match = re.search(r'[?&]table=([a-zA-Z0-9]+)', url)
    table_id = table_id_match.group(1) if table_id_match else ""
    
    if not app_token:
        raise ValueError("无法从链接中提取 app_token")
    
    if not table_id:
        raise ValueError("链接必须包含 table=tbl...（飞书表格链接）")
    
    return app_token, table_id
