"""
采集 API 路由
"""
from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import (
    CollectRequest,
    CollectResponse,
    SingleNoteCollectRequest,
    ProfileInfoCollectRequest,
    KeywordCollectRequest,
)
from app.services.apikey_validator import validate_api_key
from app.services.xhs_collector import XhsCollector, parse_feishu_table_url
from app.services.feishu_writer import write_to_feishu


router = APIRouter()


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
async def collect_notes(request: CollectRequest) -> CollectResponse:
    """
    采集小红书博主笔记
    
    - 验证 API Key
    - 请求博主主页
    - 提取笔记列表
    - 循环采集笔记详情
    - 返回飞书表格记录格式的数据
    """
    
    # 1. 验证 API Key
    validation_result = await validate_api_key(request.apiKey)
    
    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error
        )
    
    # 2. 解析飞书表格链接
    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e)
        )
    
    # 3. 创建采集器
    user_agent = request.userAgent or settings.DEFAULT_USER_AGENT
    collector = XhsCollector(cookie=request.cookie, user_agent=user_agent)
    
    # 4. 执行采集
    try:
        records, success_count, fail_count, failed_note_ids = await collector.collect_all_notes(
            profile_url=request.bozhulianjie,
            max_notes=request.maxNotes
        )
        
        # 5. 构建响应
        if success_count == 0 and fail_count > 0:
            return CollectResponse(
                success=False,
                code=500,
                message=f"采集失败，共 {fail_count} 条笔记全部失败",
                appToken=app_token,
                tableId=table_id,
                records=[],
                totalCount=0,
                error=f"失败的笔记ID: {', '.join(failed_note_ids[:5])}..."
            )
        
        message = f"成功采集 {success_count} 条笔记"
        if fail_count > 0:
            message += f"，{fail_count} 条失败"
        
        # 6. 如果需要写入飞书表格
        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu
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
            writeCount=write_count
        )
        
    except Exception as e:
        error_msg = str(e)
        
        # 识别常见错误
        if "Cookie" in error_msg or "__INITIAL_STATE__" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg
            )
        
        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg
        )


@router.post("/collect/note", response_model=CollectResponse)
async def collect_single_note(request: SingleNoteCollectRequest) -> CollectResponse:
    """
    采集小红书单条笔记

    - 验证 API Key
    - 解析笔记链接
    - 请求笔记详情
    - 返回飞书表格记录格式的数据
    """
    validation_result = await validate_api_key(request.apiKey)

    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error
        )

    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e)
        )

    user_agent = request.userAgent or settings.DEFAULT_USER_AGENT
    collector = XhsCollector(cookie=request.cookie, user_agent=user_agent)

    try:
        note_info = await collector.build_note_info_from_url(request.bijilianjie)
        feed_data = await collector.fetch_note_detail(note_info)
        record = collector.process_note_detail(feed_data, note_info)

        records = [record]
        message = "成功采集 1 条笔记"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu
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
            writeCount=write_count
        )
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="笔记链接格式错误或缺少 xsec_token",
            appToken=app_token,
            tableId=table_id,
            error=str(e)
        )
    except Exception as e:
        error_msg = str(e)

        if "Cookie" in error_msg or "__INITIAL_STATE__" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg
        )


@router.post("/collect/profile-info", response_model=CollectResponse)
async def collect_profile_info(request: ProfileInfoCollectRequest) -> CollectResponse:
    """
    采集小红书博主信息

    - 验证 API Key
    - 请求博主主页
    - 提取博主信息
    - 返回飞书表格记录格式的数据
    """
    validation_result = await validate_api_key(request.apiKey)

    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error
        )

    try:
        app_token, table_id = parse_feishu_table_url(request.biaogelianjie)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e)
        )

    user_agent = request.userAgent or settings.DEFAULT_USER_AGENT
    collector = XhsCollector(cookie=request.cookie, user_agent=user_agent)

    try:
        html_content, clean_url = await collector.fetch_homepage_html(request.bozhulianjie)
        record = collector.extract_user_profile(html_content, clean_url)

        records = [record]
        message = "成功采集 1 条博主信息"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu
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
            writeCount=write_count
        )
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="博主链接格式错误",
            appToken=app_token,
            tableId=table_id,
            error=str(e)
        )
    except Exception as e:
        error_msg = str(e)

        if "Cookie" in error_msg or "__INITIAL_STATE__" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg
        )


@router.post("/collect/keyword", response_model=CollectResponse)
async def collect_keyword_notes(request: KeywordCollectRequest) -> CollectResponse:
    """
    根据关键词采集小红书笔记

    - 验证 API Key
    - 关键词搜索笔记列表
    - 循环采集笔记详情
    - 返回飞书表格记录格式的数据
    """
    validation_result = await validate_api_key(request.apiKey)

    if not validation_result.success:
        return CollectResponse(
            success=False,
            code=validation_result.code,
            message=validation_result.message,
            error=validation_result.error
        )

    keyword = request.keyword.strip()
    if not keyword:
        return CollectResponse(
            success=False,
            code=400,
            message="关键词不能为空",
            error="keyword is empty"
        )

    table_url = request.biaogelianjie or settings.DEFAULT_FEISHU_TABLE_URL
    if not table_url:
        return CollectResponse(
            success=False,
            code=400,
            message="缺少飞书表格链接",
            error="biaogelianjie is required"
        )

    try:
        app_token, table_id = parse_feishu_table_url(table_url)
    except ValueError as e:
        return CollectResponse(
            success=False,
            code=400,
            message="飞书表格链接格式错误",
            error=str(e)
        )

    user_agent = request.userAgent or settings.DEFAULT_USER_AGENT
    collector = XhsCollector(cookie=request.cookie, user_agent=user_agent)

    try:
        records, success_count, fail_count, failed_note_ids = await collector.collect_notes_by_keyword(
            keyword=keyword,
            max_notes=request.maxNotes,
            sort=request.sort,
            note_type=request.noteType
        )

        if success_count == 0 and fail_count > 0:
            return CollectResponse(
                success=False,
                code=500,
                message=f"关键词「{keyword}」采集失败，共 {fail_count} 条笔记全部失败",
                appToken=app_token,
                tableId=table_id,
                records=[],
                totalCount=0,
                error=f"失败的笔记ID: {', '.join(failed_note_ids[:5])}..."
            )

        message = f"关键词「{keyword}」成功采集 {success_count} 条笔记"
        if fail_count > 0:
            message += f"，{fail_count} 条失败"

        write_success, write_count, write_message = await _write_records_if_needed(
            app_token,
            table_id,
            records,
            request.writeToFeishu
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
            writeCount=write_count
        )
    except Exception as e:
        error_msg = str(e)

        if "Cookie" in error_msg or "__INITIAL_STATE__" in error_msg:
            return CollectResponse(
                success=False,
                code=401,
                message="Cookie 已失效，请重新获取",
                appToken=app_token,
                tableId=table_id,
                error=error_msg
            )

        return CollectResponse(
            success=False,
            code=500,
            message="采集过程发生错误",
            appToken=app_token,
            tableId=table_id,
            error=error_msg
        )
