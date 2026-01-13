# 小红书笔记采集 API 服务

基于 FastAPI 的小红书笔记数据采集接口，支持单篇笔记、博主全部笔记、博主信息采集。

## ✨ 功能特性

- 📝 单篇笔记详情采集
- 👤 博主主页信息采集
- 📚 博主全部笔记批量采集
- 🔍 关键词搜索笔记采集
- 🔐 完整的签名算法支持
- 🚀 FastAPI 高性能异步框架
- 📊 自动生成 API 文档
- 🎯 与 Coze 工作流完美集成

## 🚀 快速开始

### 方式1：Zeabur 一键部署（推荐，适合技术小白）

[![Deploy on Zeabur](https://zeabur.com/button.svg)](https://zeabur.com)

**部署步骤：**

1. 注册/登录 [Zeabur](https://zeabur.com)
2. 导入此 GitHub 仓库
3. 配置环境变量（见下方）
4. 点击部署，等待 2-5 分钟
5. 获取自动分配的域名

**详细教程：** 查看 [Zeabur部署指南.md](Zeabur部署指南.md)

### 方式2：Zeabur + 阿里云服务器（省钱方案）

如果你有阿里云服务器，可以使用 Zeabur 托管你的服务器进行部署：

1. 在 Zeabur 添加你的服务器（SSH 连接）
2. 部署时选择你的服务器
3. 享受可视化管理界面 + 零额外费用

**详细教程：** 查看 [Zeabur部署指南.md](Zeabur部署指南.md)

### 方式3：本地开发运行

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd 小红书采集Fastapi方案

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 Cookie

# 5. 启动服务
uvicorn main:app --reload

# 6. 访问 API 文档
open http://localhost:8000/docs
```

### 方式4：阿里云 ECS 手动部署

适合有一定技术基础的用户，查看 [部署指南.md](部署指南.md)

## 🔧 环境变量配置

创建 `.env` 文件（或在 Zeabur 控制台配置）：

```env
# 小红书 Cookie（必填）
XHS_COOKIE=your_cookie_here

# 服务器配置（Zeabur 会自动设置，本地开发可修改）
HOST=0.0.0.0
PORT=8080

# 日志级别（可选）
LOG_LEVEL=info
```

### 🍪 如何获取 Cookie？

1. 浏览器登录小红书 (www.xiaohongshu.com)
2. 按 F12 打开开发者工具
3. 切换到 Network (网络) 标签
4. 刷新页面
5. 点击任意请求，找到 Request Headers
6. 复制完整的 Cookie 值（从头到尾）

## 📖 API 文档

## API 接口

### POST /api/v1/collect

采集博主笔记数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "a1=xxx; web_session=xxx; ...",
  "bozhulianjie": "https://www.xiaohongshu.com/user/profile/xxx",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "maxNotes": 20,
  "userAgent": "Mozilla/5.0 ..."
}
```

**响应**:

```json
{
  "success": true,
  "code": 0,
  "message": "成功采集 16 条笔记",
  "appToken": "bascnxxx",
  "tableId": "tblxxx",
  "records": [
    {
      "fields": {
        "笔记标题": "...",
        "笔记内容": "...",
        "点赞数": 123,
        ...
      }
    }
  ],
  "totalCount": 16
}
```

### POST /api/v1/collect/note

根据笔记链接采集单条笔记数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "a1=xxx; web_session=xxx; ...",
  "bijilianjie": "https://www.xiaohongshu.com/explore/xxx?xsec_token=xxx&xsec_source=pc_user",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "userAgent": "Mozilla/5.0 ..."
}
```

**说明**: 建议提供包含 `xsec_token` 的完整链接，缺失时会尝试从详情页解析。

**响应**: 同 `/api/v1/collect`，`totalCount` 为 1。

### POST /api/v1/collect/keyword

根据关键词采集笔记数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "a1=xxx; web_session=xxx; ...",
  "keyword": "健身",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "maxNotes": 20,
  "sort": "general",
  "noteType": 0,
  "userAgent": "Mozilla/5.0 ..."
}
```

**说明**:
- `biaogelianjie` 未传时默认写入配置的表格链接
- `sort` 支持 `general`（综合）、`hot_desc`（热度）、`time_desc`（最新）
- `noteType` 取值 0/1/2，对应 全部/图文/视频

**响应**: 同 `/api/v1/collect`。

### POST /api/v1/collect/profile-info

根据博主主页链接采集博主信息。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "a1=xxx; web_session=xxx; ...",
  "bozhulianjie": "https://www.xiaohongshu.com/user/profile/xxx",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "userAgent": "Mozilla/5.0 ..."
}
```

**响应**: 同 `/api/v1/collect`，`records` 为博主信息字段。

**博主信息字段**:

| 字段名 | 类型 |
|--------|------|
| 博主ID | 文本 |
| 博主昵称 | 文本 |
| 小红书号 | 文本 |
| 个人简介 | 文本 |
| 性别 | 文本 |
| IP属地 | 文本 |
| 头像链接 | 文本 |
| 关注数 | 数字 |
| 粉丝数 | 数字 |
| 获赞与收藏 | 数字 |

## 抖音 API 接口

### POST /api/v1/douyin/collect

采集抖音博主主页视频数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "ttwid=xxx; msToken=xxx; ...",
  "bozhulianjie": "https://www.douyin.com/user/xxx",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "maxNotes": 20,
  "userAgent": "Mozilla/5.0 ...",
  "msToken": "可选"
}
```

**响应**: 同 `/api/v1/collect`。

### POST /api/v1/douyin/collect/video

采集抖音单条视频数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "ttwid=xxx; msToken=xxx; ...",
  "bijilianjie": "https://www.douyin.com/video/xxxxxxxxxxxx",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "userAgent": "Mozilla/5.0 ...",
  "msToken": "可选"
}
```

### POST /api/v1/douyin/collect/profile-info

采集抖音博主信息。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "ttwid=xxx; msToken=xxx; ...",
  "bozhulianjie": "https://www.douyin.com/user/xxx",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "userAgent": "Mozilla/5.0 ...",
  "msToken": "可选"
}
```

### POST /api/v1/douyin/collect/keyword

根据关键词采集抖音视频数据。

**请求体**:

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "ttwid=xxx; msToken=xxx; ...",
  "keyword": "Python",
  "biaogelianjie": "https://xxx.feishu.cn/base/xxx?table=tblxxx",
  "maxNotes": 20,
  "sort": "general",
  "userAgent": "Mozilla/5.0 ...",
  "msToken": "可选"
}
```

## 项目结构

```
小红书采集Fastapi方案/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── api/
│   │   └── collect.py       # 采集接口
│   ├── services/
│   │   ├── apikey_validator.py   # API Key 验证
│   │   ├── xhs_collector.py      # 小红书采集逻辑
│   │   └── xhs_sign.py           # 签名生成
│   ├── models/
│   │   └── schemas.py       # 数据模型
│   └── core/
│       └── config.py        # 配置
├── requirements.txt
├── env_example.txt
├── coze_workflow_config.md  # Coze 工作流配置指南
└── README.md
```

## 配置说明

### 飞书应用配置

1. 前往 [飞书开放平台](https://open.feishu.cn/app) 创建应用
2. 获取 App ID 和 App Secret
3. 添加多维表格权限：`bitable:record:read`、`bitable:record:write`

### API Key 管理表格

在飞书多维表格中创建 API Key 管理表，字段如下：

| 字段名 | 类型 |
|--------|------|
| api_key | 文本 |
| api_key状态 | 单选（未激活/已激活/已过期/已冻结） |
| 激活时间 | 日期时间 |
| 最后使用时间 | 日期时间 |
| 使用次数 | 数字 |

## Coze 工作流配置

详见 [coze_workflow_config.md](coze_workflow_config.md)

简化后的工作流只有 4 个节点：

```
开始 → HTTP请求 → 飞书写入 → 结束
```

## 部署

### 方式 1: 云服务器

```bash
# 1. 上传代码到服务器
# 2. 安装依赖
pip install -r requirements.txt

# 3. 使用 systemd 或 supervisor 管理进程
# 4. 配置 nginx 反向代理（可选）
```

### 方式 2: Docker（推荐）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t xhs-collector .
docker run -d -p 8000:8000 --env-file .env xhs-collector
```

## 注意事项

1. **Cookie 有效期**：通常 7-30 天，失效后需重新获取
2. **采集频率**：建议单个 Cookie 每日采集 < 5 个博主
3. **延迟保护**：内置智能延迟，请勿修改
4. **安全建议**：使用小号 Cookie，避免主账号风险

## License

MIT
