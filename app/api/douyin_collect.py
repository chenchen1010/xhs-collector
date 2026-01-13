"""
Douyin collect API routes.
"""
from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import (
    CollectResponse,
    DouyinCollectRequest,
    DouyinKeywordCollectRequest,
    DouyinProfileInfoCollectRequest,
    DouyinSingleVideoCollectRequest,
)
from app.services.apikey_validator import validate_api_key
from app.services.douyin_collector import DouyinCollector
from app.services.feishu_writer import write_to_feishu
from app.services.xhs_collector import parse_feishu_table_url


router = APIRouter(prefix="/douyin")


async def _write_records_if_needed(app_token: str, table_id: str, records, write_enabled: bool) -> tuple:
    write_success = None
    write_count = 0
    message_suffix = ""

    if write_enabled and records:
        try:
            records_dict = [
                record.dict() if hasattr(record, "dict") else record
                for record in records
            ]
            write_result = await write_to_feishu(app_token, table_id, records_dict)

            write_success = write_result.get("success", False)
            write_count = write_result.get("totalSuccess", 0)

            if write_success:
                message_suffix = f"，已写入飞书 {write_count} 条"
            else:
                message_suffix = f"，写入飞书失败: {write_result.get('message', '未知错误')}"
        except Exception as e:
            write_success = False
            message_suffix = f"，写入飞书异常: {str(e)}"

    return write_success, write_count, message_suffix


@router.post("/collect", response_model=CollectResponse)
async def collect_creator_videos(request: DouyinCollectRequest) -> CollectResponse:
    """
    采集抖音博主主页视频
    """
    validation_result = await validate_api_key(request.apiKey)
    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error,
        )

    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e),
        )

    collector = DouyinCollector(
        cookie=request.cookie,
        user_agent=request.userAgent or settings.DEFAULT_USER_AGENT,
        ms_token=request.msToken,
    )

    try:
        records, success_count, fail_count, failed_ids = await collector.collect_creator_videos(
            profile_url=request.bozhulianjie,
            max_notes=request.maxNotes,
        )

        if success_count == 0 and fail_count > 0:
            return CollectResponse(
                success=False,
                code=500,
                message=f"采集失败，共 {fail_count} 条视频全部失败",
                appToken=app_token,
                tableId=table_id,
                records=[],
                totalCount=0,
                error=f"失败的视频ID: {', '.join(failed_ids[:5])}...",
            )

        message = f"成功采集 {success_count} 条视频"
        if fail_count > 0:
            message += f"，{fail_count} 条失败"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu,
        )
        message += write_message

        return CollectResponse(
            success=True,
            code=0,
            message=message,
            appToken=app_token,
            tableId=table_id,
            records=records,
            totalCount=success_count,
            writeSuccess=write_success,
            writeCount=write_count,
        )
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="博主链接格式错误",
            appToken=app_token,
            tableId=table_id,
            error=str(e),
        )
    except Exception as e:
        error_msg = str(e)
        if "Cookie" in error_msg or "account blocked" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg,
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg,
        )


@router.post("/collect/video", response_model=CollectResponse)
async def collect_single_video(request: DouyinSingleVideoCollectRequest) -> CollectResponse:
    """
    采集抖音单条视频
    """
    validation_result = await validate_api_key(request.apiKey)
    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error,
        )

    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e),
        )

    collector = DouyinCollector(
        cookie=request.cookie,
        user_agent=request.userAgent or settings.DEFAULT_USER_AGENT,
        ms_token=request.msToken,
    )

    try:
        record = await collector.collect_single_video(request.bijilianjie)
        records = [record]
        message = "成功采集 1 条视频"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu,
        )
        message += write_message

        return CollectResponse(
            success=True,
            code=0,
            message=message,
            appToken=app_token,
            tableId=table_id,
            records=records,
            totalCount=1,
            writeSuccess=write_success,
            writeCount=write_count,
        )
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="视频链接格式错误",
            appToken=app_token,
            tableId=table_id,
            error=str(e),
        )
    except Exception as e:
        error_msg = str(e)
        if "Cookie" in error_msg or "account blocked" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg,
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg,
        )


@router.post("/collect/profile-info", response_model=CollectResponse)
async def collect_profile_info(request: DouyinProfileInfoCollectRequest) -> CollectResponse:
    """
    采集抖音博主信息
    """
    validation_result = await validate_api_key(request.apiKey)
    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error,
        )

    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e),
        )

    collector = DouyinCollector(
        cookie=request.cookie,
        user_agent=request.userAgent or settings.DEFAULT_USER_AGENT,
        ms_token=request.msToken,
    )

    try:
        record = await collector.collect_creator_profile(request.bozhulianjie)
        records = [record]
        message = "成功采集 1 条博主信息"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu,
        )
        message += write_message

        return CollectResponse(
            success=True,
            code=0,
            message=message,
            appToken=app_token,
            tableId=table_id,
            records=records,
            totalCount=1,
            writeSuccess=write_success,
            writeCount=write_count,
        )
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="博主链接格式错误",
            appToken=app_token,
            tableId=table_id,
            error=str(e),
        )
    except Exception as e:
        error_msg = str(e)
        if "Cookie" in error_msg or "account blocked" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg,
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg,
        )


@router.post("/collect/keyword", response_model=CollectResponse)
async def collect_keyword_videos(request: DouyinKeywordCollectRequest) -> CollectResponse:
    """
    根据关键词采集抖音视频
    """
    validation_result = await validate_api_key(request.apiKey)
    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error,
        )

    keyword = request.keyword.strip()
    if not keyword:
        return CollectResponse(
            success=False,
            code=400,
            message="关键词不能为空",
            error="keyword is empty",
        )

    table_url = request.biaogelianjie or settings.DEFAULT_FEISHU_TABLE_URL
    if not table_url:
        return CollectResponse(
            success=False,
            code=400,
            message="缺少飞书表格链接",
            error="biaogelianjie is required",
        )

    try:
        app_token, table_id = parse_feishu_table_url(table_url)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e),
        )

    collector = DouyinCollector(
        cookie=request.cookie,
        user_agent=request.userAgent or settings.DEFAULT_USER_AGENT,
        ms_token=request.msToken,
    )

    try:
        records, success_count, fail_count, failed_ids = await collector.collect_videos_by_keyword(
            keyword=keyword,
            max_notes=request.maxNotes,
            sort=request.sort,
        )

        if success_count == 0 and fail_count > 0:
            return CollectResponse(
                success=False,
                code=500,
                message=f"关键词「{keyword}」采集失败，共 {fail_count} 条视频全部失败",
                appToken=app_token,
                tableId=table_id,
                records=[],
                totalCount=0,
                error=f"失败的视频ID: {', '.join(failed_ids[:5])}...",
            )

        message = f"关键词「{keyword}」成功采集 {success_count} 条视频"
        if fail_count > 0:
            message += f"，{fail_count} 条失败"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu,
        )
        message += write_message

        return CollectResponse(
            success=True,
            code=0,
            message=message,
            appToken=app_token,
            tableId=table_id,
            records=records,
            totalCount=success_count,
            writeSuccess=write_success,
            writeCount=write_count,
        )
    except Exception as e:
        error_msg = str(e)
        if "Cookie" in error_msg or "account blocked" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg,
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg,
        )
