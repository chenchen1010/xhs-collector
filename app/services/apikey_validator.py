"""
API Key 验证模块
通过飞书多维表格验证 API Key 的有效性
"""
import time
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings
from app.models.schemas import APIKeyValidationResult


# 飞书表格字段名（注意：字段名有空格）
FIELD_API_KEY = "api key"
FIELD_STATUS = "api key状态"
FIELD_ACTIVATED_AT = "激活时间"
FIELD_LAST_USED_AT = "最后验证时间"
FIELD_USAGE_COUNT = "验证次数"

# 状态值
STATUS_UNACTIVATED = "未激活"
STATUS_ACTIVE = "已激活"
STATUS_EXPIRED = "已过期"
STATUS_FROZEN = "已冻结"


class APIKeyValidator:
    """API Key 验证器（使用 PersonalBaseToken 授权码方式）"""
    
    def __init__(self):
        self.api_base = settings.FEISHU_API_BASE
        self.personal_base_token = settings.FEISHU_PERSONAL_BASE_TOKEN
        self.app_token = settings.FEISHU_APIKEY_APP_TOKEN
        self.table_id = settings.FEISHU_APIKEY_TABLE_ID
    
    def _get_auth_headers(self) -> dict:
        """获取授权请求头（使用 PersonalBaseToken）"""
        return {
            "Authorization": f"Bearer {self.personal_base_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
    
    async def _search_api_key_record(self, api_key: str) -> Optional[Dict[str, Any]]:
        """查询 API Key 记录"""
        url = f"{self.api_base}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
        headers = self._get_auth_headers()
        body = {
            "filter": {
                "conjunction": "and",
                "conditions": [{
                    "field_name": FIELD_API_KEY,
                    "operator": "is",
                    "value": [api_key],
                }],
            },
            "page_size": 1,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=body)
            data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"查询 API Key 失败: {data.get('msg')}")
        
        items = data.get("data", {}).get("items", [])
        return items[0] if items else None
    
    async def _update_api_key_record(self, record_id: str, fields: Dict[str, Any]) -> None:
        """更新 API Key 记录"""
        url = f"{self.api_base}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        headers = self._get_auth_headers()
        body = {"fields": fields}
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=body)
            data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"更新 API Key 失败: {data.get('msg')}")
    
    def _extract_text(self, value: Any) -> str:
        """提取文本值"""
        if value is None:
            return ""
        if isinstance(value, dict):
            for key in ("text", "name", "value", "title"):
                if key in value:
                    return str(value.get(key, "")).strip()
            return ""
        if isinstance(value, list):
            return self._extract_text(value[0]) if value else ""
        return str(value).strip()
    
    def _extract_int(self, value: Any) -> int:
        """提取整数值"""
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, dict):
            for key in ("value", "number"):
                if key in value:
                    try:
                        return int(value.get(key) or 0)
                    except (TypeError, ValueError):
                        return 0
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return 0
    
    async def validate(self, api_key: str) -> APIKeyValidationResult:
        """
        验证 API Key

        Args:
            api_key: 待验证的 API Key

        Returns:
            验证结果
        """
        if not api_key:
            return APIKeyValidationResult(
                success=False,
                code=401,
                message="API Key 不能为空",
                error="apiKey 不能为空"
            )

        # 🚧 临时测试模式：跳过飞书验证，直接通过
        # TODO: 等授权码问题解决后移除此代码
        if api_key == "P2025685459865471":
            return APIKeyValidationResult(
                success=True,
                code=0,
                message="API Key 验证通过 (测试模式: 跳过飞书验证)"
            )

        # 检查配置
        if not self.personal_base_token or not self.app_token or not self.table_id:
            return APIKeyValidationResult(
                success=False,
                code=500,
                message="服务配置错误",
                error="缺少飞书配置（PERSONAL_BASE_TOKEN/APP_TOKEN/TABLE_ID）"
            )
        
        try:
            record = await self._search_api_key_record(api_key)
            
            if not record:
                return APIKeyValidationResult(
                    success=False,
                    code=401,
                    message="API Key 不存在",
                    error="API Key 不存在"
                )
            
            fields = record.get("fields", {})
            status = self._extract_text(fields.get(FIELD_STATUS))
            usage_count = self._extract_int(fields.get(FIELD_USAGE_COUNT))
            
            # 检查状态
            if status == STATUS_EXPIRED:
                return APIKeyValidationResult(
                    success=False,
                    code=403,
                    message="API Key 已过期",
                    error="API Key 已过期"
                )
            
            if status == STATUS_FROZEN:
                return APIKeyValidationResult(
                    success=False,
                    code=403,
                    message="API Key 已被冻结",
                    error="API Key 已被冻结"
                )
            
            if status not in (STATUS_UNACTIVATED, STATUS_ACTIVE, ""):
                return APIKeyValidationResult(
                    success=False,
                    code=403,
                    message=f"API Key 状态异常: {status}",
                    error=f"API Key 状态异常: {status}"
                )
            
            # 更新使用信息
            now_ms = int(time.time() * 1000)
            update_fields: Dict[str, Any] = {
                FIELD_LAST_USED_AT: now_ms,
                FIELD_USAGE_COUNT: usage_count + 1,
            }
            
            # 首次使用时激活
            if status == STATUS_UNACTIVATED or not status:
                update_fields[FIELD_STATUS] = STATUS_ACTIVE
                update_fields[FIELD_ACTIVATED_AT] = now_ms
            
            await self._update_api_key_record(record["record_id"], update_fields)
            
            return APIKeyValidationResult(
                success=True,
                code=0,
                message="API Key 验证通过"
            )
            
        except Exception as exc:
            return APIKeyValidationResult(
                success=False,
                code=500,
                message="API Key 验证失败",
                error=f"API Key 验证失败: {exc}"
            )


# 单例实例
_validator = APIKeyValidator()


async def validate_api_key(api_key: str) -> APIKeyValidationResult:
    """验证 API Key（便捷函数）"""
    return await _validator.validate(api_key)

