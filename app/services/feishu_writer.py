"""
飞书多维表格写入服务
负责将采集数据批量写入飞书表格
"""
import httpx
from typing import List, Dict, Any, Optional

from app.core.config import settings


FIELD_UI_TYPE_MAP = {
    "Text": 1,
    "Number": 2,
    "SingleSelect": 3,
    "MultiSelect": 4,
    "DateTime": 5,
    "Attachment": 17,
    "Formula": 20,
}


class FeishuWriter:
    """飞书多维表格写入器"""
    
    def __init__(self, app_token: str, table_id: str, token: str = None):
        self.app_token = app_token
        self.table_id = table_id
        self.base_url = settings.FEISHU_API_BASE
        # 优先使用传入的 token，否则使用配置中的写入 token
        self.token = token or settings.FEISHU_WRITE_TOKEN or settings.FEISHU_PERSONAL_BASE_TOKEN
        self._fields_cache: Optional[Dict[str, Any]] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    
    async def batch_create_records(
        self, 
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量创建多条记录
        
        Args:
            records: 记录列表，每条记录包含 fields 字段
            
        Returns:
            API 响应结果
        """
        if not records:
            return {"success": True, "message": "无数据需要写入", "count": 0}
        
        # 先根据表格字段类型做规范化处理，避免类型不匹配
        try:
            field_map = await self._get_table_fields()
            updated = await self._ensure_select_options(records, field_map)
            if updated:
                field_map = await self._get_table_fields()
            records = self._normalize_records(records, field_map)
        except Exception:
            # 获取字段信息失败时，保持原始数据写入
            pass

        # 飞书批量创建 API 限制每次最多 500 条
        batch_size = 500
        all_results = []
        total_success = 0
        total_failed = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            result = await self._create_batch(batch)
            all_results.append(result)
            
            if result.get("success"):
                total_success += result.get("count", 0)
            else:
                total_failed += len(batch)
        
        error_messages = [
            result.get("error")
            for result in all_results
            if not result.get("success") and result.get("error")
        ]
        error_message = error_messages[0] if error_messages else ""

        message = f"成功写入 {total_success} 条记录"
        if total_failed > 0:
            message += f"，{total_failed} 条失败"
            if error_message:
                message += f"，原因: {error_message}"

        return {
            "success": total_failed == 0,
            "message": message,
            "totalSuccess": total_success,
            "totalFailed": total_failed,
            "details": all_results,
            "errors": error_messages
        }
    
    async def _create_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建一批记录"""
        # base_url 已包含 /open-apis
        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
        
        # 构建请求体
        payload = {
            "records": records
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url, 
                    headers=self._get_headers(), 
                    json=payload
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "count": 0
                    }
                
                data = response.json()
                
                if data.get("code") != 0:
                    return {
                        "success": False,
                        "error": f"API 错误 ({data.get('code')}): {data.get('msg', '未知错误')}",
                        "count": 0,
                        "detail": data
                    }
                
                created_records = data.get("data", {}).get("records", [])
                return {
                    "success": True,
                    "count": len(created_records),
                    "record_ids": [r.get("record_id") for r in created_records]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "count": 0
            }

    async def _get_table_fields(self) -> Dict[str, Any]:
        """获取表格字段信息并缓存"""
        if self._fields_cache is not None:
            return self._fields_cache

        url = f"{self.base_url}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"获取表格字段失败: HTTP {response.status_code}")
            data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取表格字段失败: {data.get('msg', '未知错误')}")

        items = data.get("data", {}).get("items", [])
        field_map = {item.get("field_name"): item for item in items if item.get("field_name")}

        self._fields_cache = field_map
        return field_map

    async def _ensure_select_options(
        self,
        records: List[Dict[str, Any]],
        field_map: Dict[str, Any]
    ) -> bool:
        """确保单选/多选字段的选项包含将要写入的值"""
        pending_updates: Dict[str, set] = {}

        for record in records:
            fields = record.get("fields", {}) if isinstance(record, dict) else {}
            for raw_name, value in fields.items():
                resolved_name = self._resolve_field_name(raw_name, field_map)
                if not resolved_name:
                    continue

                field_meta = field_map.get(resolved_name)
                field_type = self._resolve_field_type(field_meta)
                if field_type not in (3, 4):
                    continue

                if field_type == 3 and resolved_name not in self._allow_single_select_any_value():
                    continue
                if field_type == 4 and resolved_name not in self._allow_multi_select_any_value():
                    continue

                option_names = {
                    opt.get("name")
                    for opt in (field_meta.get("property") or {}).get("options", [])
                    if opt.get("name")
                }
                candidate_values = self._collect_select_values(resolved_name, value, field_type)
                missing = {v for v in candidate_values if v and v not in option_names}
                if missing:
                    pending_updates.setdefault(resolved_name, set()).update(missing)

        if not pending_updates:
            return False

        updated_any = False
        for field_name, missing in pending_updates.items():
            field_meta = field_map.get(field_name)
            if not field_meta:
                continue
            success = await self._update_field_options(field_meta, missing)
            updated_any = updated_any or success

        if updated_any:
            self._fields_cache = None
        return updated_any

    def _collect_select_values(self, field_name: str, value: Any, field_type: int) -> set:
        if value is None:
            return set()

        if field_type == 3:
            if isinstance(value, list):
                value = value[0] if value else ""
            normalized = self._to_text(value)
            normalized = self._normalize_note_type(field_name, normalized, set())
            return {normalized} if normalized else set()

        values: List[str] = []
        if isinstance(value, list):
            values = [self._to_text(v) for v in value if self._to_text(v)]
        elif isinstance(value, str):
            raw = value.replace("，", ",").replace("\n", ",")
            values = [v.strip() for v in raw.split(",") if v.strip()]
        else:
            text = self._to_text(value)
            values = [text] if text else []

        return {v for v in values if v}

    async def _update_field_options(self, field_meta: Dict[str, Any], missing: set) -> bool:
        field_id = field_meta.get("field_id") or field_meta.get("fieldId")
        field_name = field_meta.get("field_name")
        field_type = self._resolve_field_type(field_meta)
        if not field_id or not field_name or not field_type:
            return False

        field_property = field_meta.get("property") or {}
        options = field_property.get("options") or []
        option_names = {opt.get("name") for opt in options if opt.get("name")}
        additions = [name for name in missing if name not in option_names]
        if not additions:
            return False

        updated_options = options + [{"name": name} for name in additions]
        payload = {
            "field_name": field_name,
            "type": field_type,
            "property": {
                **field_property,
                "options": updated_options
            }
        }

        url = (
            f"{self.base_url}/bitable/v1/apps/{self.app_token}/"
            f"tables/{self.table_id}/fields/{field_id}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=self._get_headers(), json=payload)

        if response.status_code != 200:
            return False

        data = response.json()
        return data.get("code") == 0

    def _normalize_records(
        self,
        records: List[Dict[str, Any]],
        field_map: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """按字段类型规范化记录"""
        normalized_records: List[Dict[str, Any]] = []

        for record in records:
            fields = record.get("fields", {}) if isinstance(record, dict) else {}
            normalized_fields: Dict[str, Any] = {}

            for field_name, value in fields.items():
                resolved_name = self._resolve_field_name(field_name, field_map)
                if not resolved_name:
                    continue

                field_meta = field_map.get(resolved_name)
                normalized_value = self._normalize_field_value(resolved_name, value, field_meta)
                if normalized_value is not None:
                    normalized_fields[resolved_name] = normalized_value

            normalized_records.append({
                **record,
                "fields": normalized_fields
            })

        return normalized_records

    def _normalize_field_value(
        self,
        field_name: str,
        value: Any,
        field_meta: Optional[Dict[str, Any]]
    ) -> Any:
        """根据字段类型处理字段值"""
        if value is None:
            return None

        if not field_meta:
            return value

        field_type = self._resolve_field_type(field_meta)
        field_property = field_meta.get("property") or {}
        options = field_property.get("options") or []
        option_names = {opt.get("name") for opt in options if opt.get("name")}

        # 20 Formula: 只读字段，跳过写入
        if field_type == 20:
            return None

        # 1 Text
        if field_type == 1:
            if isinstance(value, list):
                return "\n".join(self._to_text(v) for v in value if self._to_text(v))
            return self._to_text(value)

        # 2 Number
        if field_type == 2:
            return self._to_number(value)

        # 3 SingleSelect
        if field_type == 3:
            normalized = self._to_single_select_value(field_name, value, option_names)
            return normalized

        # 4 MultiSelect
        if field_type == 4:
            normalized = self._to_multi_select_value(field_name, value, option_names)
            return normalized

        # 5 DateTime (ms timestamp)
        if field_type == 5:
            return self._to_timestamp(value)

        # 17 Attachment: 跳过非附件结构，避免写入失败
        if field_type == 17:
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
            return None

        return value

    def _to_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("text", "name", "value", "title", "url"):
                if key in value:
                    return str(value.get(key, "")).strip()
            return ""
        return str(value).strip()

    def _to_number(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        text = self._to_text(value).replace(",", "")
        try:
            number = float(text)
            return int(number) if number.is_integer() else number
        except ValueError:
            return None

    def _to_timestamp(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value_int = int(value)
            if value_int < 100000000000:
                return value_int * 1000
            return value_int
        text = self._to_text(value)
        if text.isdigit():
            value_int = int(text)
            if value_int < 100000000000:
                return value_int * 1000
            return value_int
        return None

    def _resolve_field_type(self, field_meta: Optional[Dict[str, Any]]) -> Optional[int]:
        if not field_meta:
            return None

        field_type = field_meta.get("type") or field_meta.get("field_type")
        if isinstance(field_type, str) and field_type.isdigit():
            field_type = int(field_type)

        if isinstance(field_type, int):
            return field_type

        ui_type = field_meta.get("ui_type") or field_meta.get("uiType")
        if ui_type:
            return FIELD_UI_TYPE_MAP.get(ui_type)

        return None

    def _to_single_select_value(
        self,
        field_name: str,
        value: Any,
        option_names: set
    ) -> Optional[str]:
        if isinstance(value, list):
            value = value[0] if value else ""
        normalized = self._to_text(value)
        normalized = self._normalize_note_type(field_name, normalized, option_names)
        if option_names and normalized not in option_names:
            if field_name in self._allow_single_select_any_value():
                return normalized or None
            return None
        return normalized or None

    def _to_multi_select_value(
        self,
        field_name: str,
        value: Any,
        option_names: set
    ) -> Optional[List[str]]:
        values: List[str] = []
        if isinstance(value, list):
            values = [self._to_text(v) for v in value if self._to_text(v)]
        elif isinstance(value, str):
            raw = value.replace("，", ",").replace("\n", ",")
            values = [v.strip() for v in raw.split(",") if v.strip()]
        else:
            values = [self._to_text(value)] if self._to_text(value) else []

        if field_name in ("笔记标签", "标签"):
            values = [self._to_text(v) for v in values if self._to_text(v)]

        if option_names and field_name not in self._allow_multi_select_any_value():
            values = [v for v in values if v in option_names]

        return values or None

    def _normalize_note_type(self, field_name: str, value: str, option_names: set) -> str:
        if not field_name.startswith("笔记类型"):
            return value

        if value == "normal" and "图文" in option_names:
            return "图文"
        if value == "video" and "视频" in option_names:
            return "视频"
        return value

    def _allow_single_select_any_value(self) -> set:
        return {"账号名称", "博主昵称"}

    def _allow_multi_select_any_value(self) -> set:
        return {"笔记标签", "标签"}

    def _resolve_field_name(self, field_name: str, field_map: Dict[str, Any]) -> Optional[str]:
        if field_name in field_map:
            return field_name

        aliases = self._field_aliases().get(field_name, [])
        for alias in aliases:
            if alias in field_map:
                return alias
        return None

    def _field_aliases(self) -> Dict[str, List[str]]:
        return {
            # 笔记字段别名
            "笔记类型": ["笔记类型", "笔记类型1"],
            "笔记标签": ["笔记标签", "标签"],
            "图片链接": ["图片链接", "笔记封面图链接"],
            "笔记标题": ["笔记标题", "标题"],
            "笔记内容": ["笔记内容", "文案", "笔记文案", "内容"],
            "账号名称": ["账号名称", "博主昵称"],
            "头像链接": ["头像链接", "头像URL", "头像地址"],
            # 博主字段别名
            "博主昵称": ["账号名称", "博主昵称"],
            "小红书号": ["小红书ID", "小红书号", "抖音号"],
            "个人简介": ["简介", "个人简介"],
            "获赞与收藏": ["赞藏总数", "获赞与收藏", "赞藏"],
        }


async def write_to_feishu(
    app_token: str, 
    table_id: str, 
    records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    写入数据到飞书表格的便捷函数
    
    Args:
        app_token: 多维表格应用 Token
        table_id: 数据表 ID
        records: 记录列表
        
    Returns:
        写入结果
    """
    writer = FeishuWriter(app_token, table_id)
    return await writer.batch_create_records(records)
