"""
应用配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    APP_NAME: str = "小红书博主笔记采集 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 飞书授权码（PersonalBaseToken）- 推荐方式
    # 从多维表格右上角菜单获取，无需创建应用
    FEISHU_PERSONAL_BASE_TOKEN: str = ""
    
    # 飞书写入授权码（用于写入采集结果的目标表格）
    FEISHU_WRITE_TOKEN: str = ""
    
    # API Key 管理表格配置
    FEISHU_APIKEY_APP_TOKEN: str = ""
    FEISHU_APIKEY_TABLE_ID: str = ""

    # 关键词采集默认写入表格链接
    DEFAULT_FEISHU_TABLE_URL: str = (
        "https://gcn6bvkburhk.feishu.cn/base/"
        "L5yObKSElaxLxUsmgM7cwR2unyd?table=tblwDly8JAMpzhmA&view=vewYP6e30Y"
    )
    
    # 飞书多维表格 API 基础地址（授权码方式使用专用域名）
    FEISHU_API_BASE: str = "https://base-api.feishu.cn/open-apis"
    
    # 采集配置
    DEFAULT_MAX_NOTES: int = 20
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36"
    )
    
    # 延迟配置（秒）
    DELAY_BEFORE_HOME: tuple = (0.5, 2.0)  # 请求主页前延迟
    DELAY_BETWEEN_NOTES_EARLY: tuple = (3.0, 5.0)  # 前5条笔记延迟
    DELAY_BETWEEN_NOTES_MIDDLE: tuple = (4.0, 6.0)  # 6-10条笔记延迟
    DELAY_BETWEEN_NOTES_LATE: tuple = (5.0, 8.0)  # 11+条笔记延迟
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 创建全局配置实例
settings = Settings()
