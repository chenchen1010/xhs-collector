"""
请求和响应数据模型
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


class CollectRequest(BaseModel):
    """采集请求"""
    apiKey: str = Field(..., description="API Key")
    cookie: str = Field(..., description="小红书 Cookie")
    bozhulianjie: str = Field(..., description="博主主页链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")
    maxNotes: int = Field(default=20, ge=1, le=50, description="最大采集数量")
    userAgent: Optional[str] = Field(default=None, description="浏览器 User-Agent")
    writeToFeishu: bool = Field(default=True, description="是否直接写入飞书表格")


class SingleNoteCollectRequest(BaseModel):
    """单条笔记采集请求"""
    apiKey: str = Field(..., description="API Key")
    cookie: str = Field(..., description="小红书 Cookie")
    bijilianjie: str = Field(..., description="笔记链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")
    userAgent: Optional[str] = Field(default=None, description="浏览器 User-Agent")
    writeToFeishu: bool = Field(default=True, description="是否直接写入飞书表格")


class ProfileInfoCollectRequest(BaseModel):
    """博主信息采集请求"""
    apiKey: str = Field(..., description="API Key")
    cookie: str = Field(..., description="小红书 Cookie")
    bozhulianjie: str = Field(..., description="博主主页链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")
    userAgent: Optional[str] = Field(default=None, description="浏览器 User-Agent")
    writeToFeishu: bool = Field(default=True, description="是否直接写入飞书表格")


class KeywordCollectRequest(BaseModel):
    """关键词采集请求"""
    apiKey: str = Field(..., description="API Key")
    cookie: str = Field(..., description="小红书 Cookie")
    keyword: str = Field(..., min_length=1, description="搜索关键词")
    biaogelianjie: str = Field(
        default=settings.DEFAULT_FEISHU_TABLE_URL,
        description="飞书表格链接"
    )
    maxNotes: int = Field(default=20, ge=1, le=50, description="最大采集数量")
    sort: str = Field(default="general", description="排序方式: general/hot_desc/time_desc")
    noteType: int = Field(default=0, ge=0, le=2, description="笔记类型: 0全部/1图文/2视频")
    userAgent: Optional[str] = Field(default=None, description="浏览器 User-Agent")
    writeToFeishu: bool = Field(default=True, description="是否直接写入飞书表格")


class DouyinBaseRequest(BaseModel):
    """抖音采集基础请求"""
    apiKey: str = Field(..., description="API Key")
    cookie: str = Field(..., description="抖音 Cookie")
    userAgent: Optional[str] = Field(default=None, description="浏览器 User-Agent")
    msToken: Optional[str] = Field(default=None, description="抖音 msToken（可选）")
    writeToFeishu: bool = Field(default=True, description="是否直接写入飞书表格")


class DouyinCollectRequest(DouyinBaseRequest):
    """抖音博主主页视频采集请求"""
    bozhulianjie: str = Field(..., description="博主主页链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")
    maxNotes: int = Field(default=20, ge=1, le=50, description="最大采集数量")


class DouyinSingleVideoCollectRequest(DouyinBaseRequest):
    """抖音单条视频采集请求"""
    bijilianjie: str = Field(..., description="视频链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")


class DouyinProfileInfoCollectRequest(DouyinBaseRequest):
    """抖音博主信息采集请求"""
    bozhulianjie: str = Field(..., description="博主主页链接")
    biaogelianjie: str = Field(..., description="飞书表格链接")


class DouyinKeywordCollectRequest(DouyinBaseRequest):
    """抖音关键词采集请求"""
    keyword: str = Field(..., min_length=1, description="搜索关键词")
    biaogelianjie: str = Field(
        default=settings.DEFAULT_FEISHU_TABLE_URL,
        description="飞书表格链接"
    )
    maxNotes: int = Field(default=20, ge=1, le=50, description="最大采集数量")
    sort: str = Field(default="general", description="排序方式: general/most_like/latest")


class NoteRecord(BaseModel):
    """笔记记录（飞书表格格式）"""
    fields: Dict[str, Any]


class CollectResponse(BaseModel):
    """采集响应"""
    success: bool = Field(..., description="是否成功")
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="消息")
    appToken: Optional[str] = Field(default=None, description="飞书表格 App Token")
    tableId: Optional[str] = Field(default=None, description="飞书表格 Table ID")
    records: List[NoteRecord] = Field(default_factory=list, description="笔记记录列表")
    totalCount: int = Field(default=0, description="采集的笔记数量")
    writeSuccess: Optional[bool] = Field(default=None, description="写入飞书是否成功")
    writeCount: int = Field(default=0, description="成功写入飞书的记录数")
    error: Optional[str] = Field(default=None, description="错误详情")


class NoteInfo(BaseModel):
    """笔记信息（从主页提取）"""
    noteId: str
    xsecToken: str
    displayTitle: str = ""
    type: str = ""
    userNickname: str = ""
    userId: str = ""
    userAvatar: str = ""
    userHomePage: str = ""


class APIKeyValidationResult(BaseModel):
    """API Key 验证结果"""
    success: bool
    code: int
    message: str
    error: Optional[str] = None
