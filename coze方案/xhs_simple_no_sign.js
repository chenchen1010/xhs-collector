// 小红书单条笔记采集 - 无签名简化版
// 直接使用 Cookie 请求,不生成签名
// 输入参数: bijilianjie, cookie
// 输出: records

// ==================== 提取函数 ====================
function extractNoteIdFromUrl(noteUrl) {
    noteUrl = noteUrl.trim();
    const patterns = [/\/explore\/([a-zA-Z0-9]+)/, /\/discovery\/item\/([a-zA-Z0-9]+)/];
    for (const pattern of patterns) {
        const match = noteUrl.match(pattern);
        if (match) return match[1];
    }
    throw new Error(`无法从 URL 中提取笔记 ID: ${noteUrl}`);
}

function extractQueryParam(noteUrl, key) {
    const match = noteUrl.match(new RegExp(`[?&]${key}=([^&]+)`));
    if (match) {
        return decodeURIComponent(match[1]);
    }
    return "";
}

function extractXsecTokenFromUrl(noteUrl) {
    return extractQueryParam(noteUrl, "xsec_token") || "";
}

function extractXsecSourceFromUrl(noteUrl) {
    return extractQueryParam(noteUrl, "xsec_source") || "";
}

// ==================== API 请求 ====================
async function fetchNoteDetail(noteId, xsecToken, xsecSource, cookie, userAgent) {
    const apiUrl = "https://edith.xiaohongshu.com/api/sns/web/v1/feed";

    const payload = {
        source_note_id: noteId,
        image_formats: ["jpg", "webp", "avif"],
        extra: { need_body_topic: "1" },
        xsec_source: xsecSource,
        xsec_token: xsecToken
    };

    console.log("[请求] 不使用签名,仅用 Cookie");

    const headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": `https://www.xiaohongshu.com/explore/${noteId}`,
        "User-Agent": userAgent,
        "Cookie": cookie
    };

    const response = await fetch(apiUrl, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload)
    });

    console.log("[响应] 状态码:", response.status);
    const responseText = await response.text();
    console.log("[响应] 内容长度:", responseText.length);

    if (response.status === 461) {
        throw new Error("参数无效,可能需要刷新 xsec_token");
    }

    if (response.status === 406) {
        throw new Error("需要签名验证 (406),此方法不支持");
    }

    if (response.status !== 200) {
        console.log("[错误] 响应内容:", responseText.substring(0, 500));
        throw new Error(`请求失败: HTTP ${response.status}`);
    }

    const data = JSON.parse(responseText);

    if (data.code === -100) {
        throw new Error("Cookie 已失效,请重新获取");
    }

    if (data.code !== 0) {
        throw new Error(`API 返回错误: ${data.msg || data.code || 'unknown'}`);
    }

    console.log("[成功] 获取到笔记数据");
    return data;
}

// ==================== 数据处理 ====================
function processNoteDetail(feedData, noteId, xsecToken, xsecSource) {
    const items = feedData?.data?.items || [];
    if (items.length === 0) {
        throw new Error("响应中没有笔记数据");
    }

    const noteItem = items[0];
    const noteCard = noteItem.note_card || {};
    const user = noteCard.user || {};
    const interactInfo = noteCard.interact_info || {};
    const imageList = noteCard.image_list || [];
    const tagList = noteCard.tag_list || [];
    const video = noteCard.video || {};

    console.log("[数据] 笔记标题:", noteCard.title);
    console.log("[数据] 图片数量:", imageList.length);

    // 提取图片链接
    const imageText = imageList
        .map(img => img.url_default || img.url_pre || img.url || "")
        .filter(url => url)
        .join("\n");

    // 提取封面
    let coverUrl = "";
    if (noteCard.cover) {
        coverUrl = noteCard.cover.url_default || noteCard.cover.url_pre || noteCard.cover.url || "";
    }
    if (!coverUrl && imageList.length > 0) {
        coverUrl = imageList[0].url_default || imageList[0].url_pre || imageList[0].url || "";
    }

    // 提取标签
    const tagsArray = tagList
        .filter(tag => tag.type === "topic" && tag.name)
        .map(tag => tag.name);

    // 提取视频链接
    let videoUrl = "";
    if (video) {
        if (video.origin_video_key) {
            videoUrl = `https://sns-video-qc.xhscdn.com/${video.origin_video_key}`;
        } else if (video.url) {
            videoUrl = video.url;
        }
    }

    // 提取互动数据
    const likedCount = parseInt(interactInfo.liked_count || 0) || 0;
    const collectedCount = parseInt(interactInfo.collected_count || 0) || 0;
    const commentCount = parseInt(interactInfo.comment_count || 0) || 0;
    const shareCount = parseInt(interactInfo.share_count || 0) || 0;
    const publishTime = noteCard.time || 0;

    // 提取用户信息
    const userNickname = user.nickname || user.nickName || user.nick_name || "";
    const userId = user.user_id || user.userId || "";
    const userAvatar = user.avatar || user.avatar_url || user.avatarUrl || "";
    const userHomePage = userId ? `https://www.xiaohongshu.com/user/profile/${userId}` : "";

    const noteUrl = `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${xsecToken}&xsec_source=${xsecSource}`;

    return {
        fields: {
            "图片链接": imageText,
            "笔记封面图链接": coverUrl,
            "笔记标题": noteCard.title || noteCard.display_title || "",
            "笔记内容": noteCard.desc || "",
            "笔记类型": noteCard.type || "",
            "笔记链接": noteUrl,
            "笔记标签": tagsArray,
            "账号名称": userNickname,
            "主页链接": userHomePage,
            "头像链接": userAvatar,
            "分享数": shareCount,
            "点赞数": likedCount,
            "收藏数": collectedCount,
            "评论数": commentCount,
            "视频链接": videoUrl,
            "发布时间": publishTime
        }
    };
}

// ==================== 主函数 ====================
async function main({ params }: Args): Promise<Output> {
    console.log("========== 开始采集 (无签名模式) ==========");

    // 获取参数
    const noteUrl = (params.bijilianjie || params.note_url || params.noteUrl || "").trim();
    const cookie = (params.cookie || "").trim().replace(/\r/g, "").replace(/\n/g, "");

    console.log("[参数] URL长度:", noteUrl.length);
    console.log("[参数] Cookie长度:", cookie.length);

    // 验证参数
    if (!noteUrl) {
        throw new Error("缺少笔记链接");
    }
    if (!cookie) {
        throw new Error("缺少 Cookie");
    }
    if (!noteUrl.startsWith("http")) {
        throw new Error("链接格式不正确");
    }

    // 提取信息
    const noteId = extractNoteIdFromUrl(noteUrl);
    console.log("[提取] 笔记ID:", noteId);

    let xsecToken = extractXsecTokenFromUrl(noteUrl).replace(/\s/g, "");
    const xsecSource = extractXsecSourceFromUrl(noteUrl) || "pc_user";

    if (!xsecToken) {
        throw new Error("链接缺少 xsec_token 参数,请提供完整链接");
    }

    console.log("[提取] Token长度:", xsecToken.length);
    console.log("[提取] Source:", xsecSource);

    // 请求数据
    const userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0";

    const feedData = await fetchNoteDetail(noteId, xsecToken, xsecSource, cookie, userAgent);

    // 处理数据
    const record = processNoteDetail(feedData, noteId, xsecToken, xsecSource);

    console.log("========== 采集完成 ✓ ==========");
    console.log("[结果] 标题:", record.fields["笔记标题"]);
    console.log("[结果] 账号:", record.fields["账号名称"]);

    return {
        records: [record]
    };
}
