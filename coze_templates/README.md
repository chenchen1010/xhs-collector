# 小红书采集 Coze 工作流模板

## 📦 项目简介

将小红书采集功能改造为 **Coze 工作流模板**，用户无需服务器，直接在 Coze 中导入模板即可使用。

**核心优势**：
- ✅ **零服务器成本**：无需部署 FastAPI 服务器
- ✅ **零技术门槛**：用户只需导入 Coze 模板
- ✅ **完全免费**：用户无限次使用，无配额限制
- ✅ **自动签名**：内置签名生成逻辑，无需手动操作

## 📂 文件说明

### 已完成的模板

| 文件名 | 功能 | 文档 |
|--------|------|------|
| [`xhs_single_note.py`](./xhs_single_note.py) | 小红书单条笔记采集 | [使用指南](../docs/小红书单条笔记采集-Coze使用指南.md) |

### 待开发的模板

| 功能 | 状态 | 说明 |
|------|------|------|
| 博主笔记采集 | 🔜 规划中 | 采集博主全部笔记 |
| 博主信息采集 | 🔜 规划中 | 采集博主个人信息 |
| 关键词搜索采集 | 🔜 规划中 | 根据关键词搜索笔记 |
| 抖音视频采集 | 🔜 规划中 | 采集抖音视频数据 |

## 🚀 快速开始

### 1. 选择模板

根据您的需求选择对应的模板：
- **单条笔记采集**：适合采集具体的笔记链接

### 2. 在 Coze 中创建工作流

1. 登录 [Coze 平台](https://www.coze.cn/)
2. 创建新工作流
3. 添加节点：开始 → 代码 → 飞书 → 结束

### 3. 配置代码节点

1. 复制对应模板的完整代码
2. 粘贴到 Coze 代码节点中
3. 配置输入参数（连接到开始节点）
4. 配置输出参数（连接到飞书节点）

### 4. 配置飞书节点

1. 使用 PersonalBaseToken 授权
2. 选择目标表格
3. 字段映射：自动映射

### 5. 运行测试

输入测试数据，验证工作流正常运行。

## 📖 详细文档

每个模板都有对应的详细使用指南，位于 [`docs/`](../docs/) 目录：

- [小红书单条笔记采集-Coze使用指南](../docs/小红书单条笔记采集-Coze使用指南.md)

## 🔑 关键改动说明

### 从 FastAPI 到 Coze 的改造

| 原 FastAPI 版本 | Coze 版本 | 说明 |
|-----------------|-----------|------|
| `async def` | `async def main(args)` | Coze 入口函数 |
| `httpx.AsyncClient` | `requests` | 使用同步请求 |
| `await client.get()` | `requests.get()` | 移除 async/await |
| `from app.services import XhsSign` | 内嵌签名代码 | 所有依赖内嵌到单文件 |
| FastAPI 路由 | - | 无需路由，直接返回数据 |

### 输入参数获取

**FastAPI 版本**：
```python
async def collect_note(request: CollectRequest):
    cookie = request.cookie
    note_url = request.bijilianjie
```

**Coze 版本**：
```python
async def main(args):
    params = args.params
    cookie = params.cookie
    note_url = params.bijilianjie
```

### 返回格式

**FastAPI 版本**：
```python
return CollectResponse(
    success=True,
    records=[record]
)
```

**Coze 版本**：
```python
return {
    "records": [record]
}
```

## ⚙️ 飞书表格字段说明

所有模板输出的数据字段与飞书表格字段对应关系，请参考各模板的文档。

**通用字段类型说明**：
- **文本字段**：笔记标题、笔记内容、笔记链接等
- **数字字段**：点赞数、收藏数、评论数、分享数、发布时间
- **多选字段**：笔记标签
- **单选字段**：笔记类型

## 🛠️ 开发指南

### 如何从 FastAPI 版本改造新模板

1. **读取源代码**：
   - 位于 `app/services/xhs_collector.py`
   - 位于 `app/services/xhs_sign.py`

2. **提取核心逻辑**：
   - 复制采集逻辑函数
   - 复制签名生成类

3. **移除异步**：
   - 删除 `async` 和 `await` 关键字
   - 将 `httpx` 改为 `requests`

4. **内嵌依赖**：
   - 将所有依赖的类和函数复制到同一文件
   - 确保单文件可独立运行

5. **改造入口**：
   ```python
   async def main(args):
       params = args.params
       # 获取输入参数
       # ... 采集逻辑
       return {"records": records}
   ```

6. **测试验证**：
   - 在 Coze 中创建工作流
   - 粘贴代码测试运行
   - 确认数据正确写入飞书

## 📋 TODO

- [ ] 完成博主笔记采集模板
- [ ] 完成博主信息采集模板
- [ ] 完成关键词搜索模板
- [ ] 完成抖音视频采集模板
- [ ] 创建工作流 JSON 导出文件
- [ ] 录制视频教程

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**最后更新**：2026-01-12
