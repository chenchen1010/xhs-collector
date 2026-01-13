# Coze 简化工作流配置指南

本文档说明如何在 Coze 中配置简化版工作流（4 节点）。

## 工作流概览

```
开始节点 → HTTP请求节点 → 飞书批量写入 → 结束节点
```

---

## 节点 1: 开始节点

### 输入参数配置

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|:----:|--------|------|
| apiKey | String | ✓ | - | API Key，用于权限验证 |
| cookie | String | ✓ | - | 小红书 Cookie |
| bozhulianjie | String | ✓ | - | 博主主页链接 |
| biaogelianjie | String | ✓ | - | 飞书表格链接（含 table=tbl...） |
| maxNotes | Integer | ✗ | 20 | 最大采集数量（1-50） |
| userAgent | String | ✗ | - | 自定义 User-Agent |

---

## 节点 2: HTTP 请求节点

### 基本配置

- **请求方式**: POST
- **URL**: `https://your-server.com/api/v1/collect`
- **超时时间**: 180 秒（重要！）

### Headers 配置

```
Content-Type: application/json
```

### Body 配置（JSON）

```json
{
  "apiKey": "{{开始节点.apiKey}}",
  "cookie": "{{开始节点.cookie}}",
  "bozhulianjie": "{{开始节点.bozhulianjie}}",
  "biaogelianjie": "{{开始节点.biaogelianjie}}",
  "maxNotes": {{开始节点.maxNotes}},
  "userAgent": "{{开始节点.userAgent}}"
}
```

### 输出配置

HTTP 请求节点会返回以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | Boolean | 是否成功 |
| code | Integer | 状态码 |
| message | String | 消息 |
| appToken | String | 飞书表格 App Token |
| tableId | String | 飞书表格 Table ID |
| records | Array | 笔记记录列表 |
| totalCount | Integer | 采集的笔记数量 |
| error | String | 错误详情（失败时） |

---

## 节点 3: 飞书多维表格 - 新增记录

### 插件选择

- **插件**: 飞书多维表格
- **API**: add_records（批量新增记录）

### 参数配置

| 参数 | 值 |
|------|-----|
| app_token | `{{HTTP请求节点.appToken}}` |
| table_id | `{{HTTP请求节点.tableId}}` |
| records | `{{HTTP请求节点.records}}` |

### 错误处理

- **processType**: continue（继续执行）
- **timeoutMs**: 180000（3分钟）

---

## 节点 4: 结束节点

### 输出配置

| 输出字段 | 来源 |
|---------|------|
| success | `{{HTTP请求节点.success}}` |
| message | `{{HTTP请求节点.message}}` |
| totalCount | `{{HTTP请求节点.totalCount}}` |
| error | `{{HTTP请求节点.error}}` |

---

## 连线配置

```
开始节点 ────────────────→ HTTP请求节点
                                │
                                ↓
                          飞书批量写入
                                │
                                ↓
                            结束节点
```

---

## 测试步骤

### 1. 本地测试（使用 ngrok）

```bash
# 启动本地服务
cd 小红书采集Fastapi方案
uvicorn app.main:app --reload --port 8000

# 另一个终端，启动 ngrok
ngrok http 8000
```

ngrok 会提供一个公网 URL，如 `https://xxxx.ngrok.io`

### 2. 配置 Coze 工作流

将 HTTP 请求节点的 URL 设置为 ngrok 提供的地址：
```
https://xxxx.ngrok.io/api/v1/collect
```

### 3. 运行测试

在 Coze 中运行工作流，输入测试参数：

```json
{
  "apiKey": "P2025685459865471",
  "cookie": "a1=xxx; web_session=xxx; ...",
  "bozhulianjie": "https://www.xiaohongshu.com/user/profile/66b4c79d000000001d031033",
  "biaogelianjie": "https://xxx.feishu.cn/base/bascnxxx?table=tblxxxxxxxxxxxx",
  "maxNotes": 5
}
```

---

## 常见问题

### Q1: HTTP 请求超时

**解决方案**:
- 确保超时时间设置为 180 秒
- 减少 maxNotes 数量（如设为 10）
- 检查服务器网络状况

### Q2: Cookie 失效

**错误信息**: `Cookie 已失效，请重新获取`

**解决方案**:
- 重新从浏览器获取 Cookie
- 确保使用小红书网页版 Cookie
- Cookie 有效期通常为 7-30 天

### Q3: API Key 验证失败

**解决方案**:
- 检查 API Key 是否正确
- 确认 API Key 状态（未过期、未冻结）
- 检查服务端飞书配置

### Q4: 飞书写入失败

**解决方案**:
- 确认表格字段类型匹配（特别是"笔记标签"需为多选类型）
- 检查飞书表格权限
- 确认 app_token 和 table_id 正确

---

## 飞书表格字段配置

确保飞书表格包含以下 15 个字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 图片链接 | 文本 | 多张图片用换行分隔 |
| 笔记标题 | 文本 | |
| 笔记内容 | 文本 | |
| 笔记类型 | 文本 | normal/video |
| 笔记链接 | 文本 | |
| 笔记标签 | **多选** | 允许动态添加选项 |
| 账号名称 | **单选** | 允许动态添加选项 |
| 主页链接 | 文本 | |
| 头像链接 | 文本 | |
| 分享数 | 数字 | |
| 点赞数 | 数字 | |
| 收藏数 | 数字 | |
| 评论数 | 数字 | |
| 视频链接 | 文本 | |
| 发布时间 | 日期 | 毫秒时间戳 |

**重要**：`笔记标签` 和 `账号名称` 必须开启"允许动态添加选项"！



