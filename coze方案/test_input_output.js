// 测试 Coze 代码节点输入输出 - 逐步加入业务逻辑
// 步骤1: 输入输出验证 ✓
// 步骤2: URL 解析和参数提取
// 步骤3: Cookie 解析

async function main({ params }: Args): Promise<Output> {
    // ========== 调试信息:打印所有输入参数 ==========
    console.log("========== 步骤1: 输入参数调试信息 ==========");
    console.log("params 对象:", JSON.stringify(params, null, 2));

    // ========== 获取输入参数 ==========
    const noteUrl = (params.bijilianjie || "").trim();
    const cookie = (params.cookie || "").trim().replace(/\r/g, "").replace(/\n/g, "");

    console.log("========== 步骤1: 参数提取结果 ==========");
    console.log("noteUrl 类型:", typeof noteUrl);
    console.log("noteUrl 长度:", noteUrl.length);
    console.log("noteUrl 前100字符:", noteUrl.substring(0, 100));
    console.log("cookie 类型:", typeof cookie);
    console.log("cookie 长度:", cookie.length);
    console.log("cookie 前100字符:", cookie.substring(0, 100));

    // ========== 参数验证 ==========
    const errors = [];

    if (!noteUrl) {
        errors.push("缺少笔记链接 bijilianjie");
    } else if (!noteUrl.startsWith("http")) {
        errors.push("笔记链接格式不正确,必须以 http 开头");
    }

    if (!cookie) {
        errors.push("缺少 cookie");
    }

    if (errors.length > 0) {
        console.log("========== 验证失败 ==========");
        console.log("错误列表:", errors);
        throw new Error(errors.join("; "));
    }

    console.log("========== 步骤1: 验证通过 ✓ ==========");

    // ========== 步骤2: URL 解析 ==========
    console.log("========== 步骤2: 开始 URL 解析 ==========");

    // 提取 note_id
    function extractNoteIdFromUrl(url) {
        const patterns = [/\/explore\/([a-zA-Z0-9]+)/, /\/discovery\/item\/([a-zA-Z0-9]+)/];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        throw new Error(`无法从 URL 中提取笔记 ID: ${url}`);
    }

    // 提取 URL 参数
    function extractQueryParam(url, key) {
        const match = url.match(new RegExp(`[?&]${key}=([^&]+)`));
        if (match) {
            return decodeURIComponent(match[1]);
        }
        return "";
    }

    let noteId = "";
    let xsecToken = "";
    let xsecSource = "";

    try {
        noteId = extractNoteIdFromUrl(noteUrl);
        console.log("提取到的 note_id:", noteId);

        xsecToken = extractQueryParam(noteUrl, "xsec_token").replace(/\s/g, "");
        console.log("提取到的 xsec_token 长度:", xsecToken.length);
        console.log("提取到的 xsec_token 前50字符:", xsecToken.substring(0, 50));

        xsecSource = extractQueryParam(noteUrl, "xsec_source") || "pc_user";
        console.log("提取到的 xsec_source:", xsecSource);

        console.log("========== 步骤2: URL 解析完成 ✓ ==========");
    } catch (e) {
        console.log("========== 步骤2: URL 解析失败 ✗ ==========");
        console.log("错误:", e.message);
        throw e;
    }

    // ========== 步骤3: Cookie 解析 ==========
    console.log("========== 步骤3: 开始 Cookie 解析 ==========");

    function parseCookies(cookieStr) {
        const cookies = {};
        for (const pair of cookieStr.split(';')) {
            const [key, ...valueParts] = pair.trim().split('=');
            if (key) {
                cookies[key.trim()] = valueParts.join('=').trim();
            }
        }
        return cookies;
    }

    const cookieDict = parseCookies(cookie);
    const a1Value = cookieDict.a1 || "";

    console.log("Cookie 键数量:", Object.keys(cookieDict).length);
    console.log("Cookie 主要键:", Object.keys(cookieDict).slice(0, 10).join(", "));
    console.log("a1 值长度:", a1Value.length);
    console.log("a1 值前20字符:", a1Value.substring(0, 20));

    if (!a1Value) {
        console.log("========== 步骤3: Cookie 缺少 a1 ✗ ==========");
        throw new Error("Cookie 中缺少 a1 参数");
    }

    console.log("========== 步骤3: Cookie 解析完成 ✓ ==========");

    // ========== 步骤4: 检查是否需要从 HTML 获取 xsec_token ==========
    console.log("========== 步骤4: 检查 xsec_token ==========");

    if (!xsecToken) {
        console.log("URL 中没有 xsec_token, 需要从 HTML 中提取");
        throw new Error("URL 缺少 xsec_token 参数，请提供完整的笔记链接（包含 ?xsec_token=...）");
    } else {
        console.log("URL 中已有 xsec_token, 无需从 HTML 提取 ✓");
    }

    console.log("========== 步骤4: xsec_token 验证完成 ✓ ==========");

    // ========== 步骤5: 发起 API 请求获取笔记详情 ==========
    console.log("========== 步骤5: 开始请求笔记详情 ==========");

    const apiUrl = "https://edith.xiaohongshu.com/api/sns/web/v1/feed";
    const userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0";

    const payload = {
        source_note_id: noteId,
        image_formats: ["jpg", "webp", "avif"],
        extra: { need_body_topic: "1" },
        xsec_source: xsecSource,
        xsec_token: xsecToken
    };

    console.log("API URL:", apiUrl);
    console.log("请求 payload:", JSON.stringify(payload, null, 2));

    // 暂时不生成签名，先测试不带签名的请求
    const headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": `https://www.xiaohongshu.com/explore/${noteId}`,
        "User-Agent": userAgent,
        "Cookie": cookie
    };

    console.log("请求头（部分）:", {
        "Content-Type": headers["Content-Type"],
        "Origin": headers["Origin"],
        "Referer": headers["Referer"],
        "Cookie长度": cookie.length
    });

    let feedData;
    try {
        console.log("发起 fetch 请求...");
        const response = await fetch(apiUrl, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(payload)
        });

        console.log("响应状态码:", response.status);

        const responseText = await response.text();
        console.log("响应内容长度:", responseText.length);
        console.log("响应内容前200字符:", responseText.substring(0, 200));

        if (response.status === 406) {
            console.log("========== 步骤5: 签名验证失败 (406) ==========");
            throw new Error("签名验证失败，需要添加 x-s 等签名头");
        }

        if (response.status !== 200) {
            console.log("========== 步骤5: API 请求失败 ==========");
            throw new Error(`API 请求失败: HTTP ${response.status}, 响应: ${responseText.substring(0, 200)}`);
        }

        feedData = JSON.parse(responseText);
        console.log("解析后的 JSON 数据:", JSON.stringify(feedData, null, 2).substring(0, 500));

        if (feedData.code === -100) {
            throw new Error("Cookie 已失效，请重新获取");
        }

        if (feedData.code !== 0) {
            throw new Error(`API 返回错误: ${feedData.msg || feedData.code || 'unknown'}`);
        }

        console.log("========== 步骤5: API 请求成功 ✓ ==========");

    } catch (e) {
        console.log("========== 步骤5: 请求失败 ✗ ==========");
        console.log("错误:", e.message);
        throw e;
    }

    // ========== 步骤6: 处理笔记数据 ==========
    console.log("========== 步骤6: 开始处理笔记数据 ==========");

    const items = feedData?.data?.items || [];
    console.log("items 数量:", items.length);

    if (items.length === 0) {
        throw new Error("API 响应中没有找到笔记数据");
    }

    const noteItem = items[0];
    const noteCard = noteItem.note_card || {};
    const user = noteCard.user || {};
    const interactInfo = noteCard.interact_info || {};
    const imageList = noteCard.image_list || [];
    const tagList = noteCard.tag_list || [];
    const video = noteCard.video || {};

    console.log("笔记标题:", noteCard.title);
    console.log("笔记类型:", noteCard.type);
    console.log("图片数量:", imageList.length);
    console.log("标签数量:", tagList.length);

    // 提取图片链接
    const imageText = imageList
        .map(img => img.url_default || img.url_pre || img.url || "")
        .filter(url => url)
        .join("\n");

    // 提取封面
    let coverUrl = noteCard.cover?.url_default || noteCard.cover?.url_pre || noteCard.cover?.url || "";
    if (!coverUrl && imageList.length > 0) {
        coverUrl = imageList[0].url_default || imageList[0].url_pre || imageList[0].url || "";
    }

    // 提取标签
    const tagsArray = tagList
        .filter(tag => tag.type === "topic" && tag.name)
        .map(tag => tag.name);

    // 提取视频链接
    function extractVideoUrl(videoInfo) {
        if (!videoInfo || typeof videoInfo !== 'object') return "";

        const keys = ["origin_video_key", "originVideoKey", "url", "url_default"];
        for (const key of keys) {
            if (videoInfo[key]) {
                const val = String(videoInfo[key]);
                if (val.startsWith("http")) return val;
                if (val.startsWith("//")) return `https:${val}`;
            }
        }
        return "";
    }

    const videoUrl = extractVideoUrl(video);

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

    console.log("========== 步骤6: 数据处理完成 ✓ ==========");

    // ========== 构建最终输出 ==========
    const ret = {
        records: [{
            fields: {
                "图片链接": imageText,
                "笔记封面图链接": coverUrl,
                "笔记标题": noteCard.title || noteCard.display_title || "",
                "笔记内容": noteCard.desc || "",
                "笔记类型": noteCard.type || "",
                "笔记链接": `https://www.xiaohongshu.com/explore/${noteId}?xsec_token=${xsecToken}&xsec_source=${xsecSource}`,
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
        }]
    };

    console.log("========== 最终输出 ==========");
    console.log("records 数量:", ret.records.length);
    console.log("笔记标题:", ret.records[0].fields["笔记标题"]);
    console.log("账号名称:", ret.records[0].fields["账号名称"]);

    return ret;
}
