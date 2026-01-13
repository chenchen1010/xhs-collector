# 小红书采集 Coze 工作流模板分发方案

## 项目概述

将小红书采集功能打包成 **Coze 工作流模板**，用户导入模板后配置自己的 Cookie 即可使用。

**核心优势**：
- ✅ **零服务器成本**：无需部署 FastAPI 服务器
- ✅ **零技术门槛**：用户只需导入 Coze 模板
- ✅ **完全免费**：用户无限次使用，无配额限制
- ✅ **易于维护**：更新模板即可，所有用户自动同步

**用户使用流程**：
1. 在 Coze 中导入工作流模板（通过分享链接或 JSON 文件）
2. 配置自己的小红书 Cookie（或抖音 Cookie）
3. 配置飞书多维表格写入授权码
4. 运行工作流，输入博主链接或笔记链接
5. 自动采集数据并写入飞书表格

## 当前代码库分析

目录：`/Users/burning/Desktop/Code/Coze代码开发/小红书采集Fastapi方案`

### 核心采集逻辑（可复用于 Coze）
以下代码可以直接移植到 Coze 代码节点：
- [app/services/xhs_collector.py](../小红书采集Fastapi方案/app/services/xhs_collector.py) - 小红书采集核心逻辑
- [app/services/xhs_sign.py](../小红书采集Fastapi方案/app/services/xhs_sign.py) - 小红书签名生成
- [app/services/douyin_collector.py](../小红书采集Fastapi方案/app/services/douyin_collector.py) - 抖音采集逻辑
- [app/services/douyin_sign.py](../小红书采集Fastapi方案/app/services/douyin_sign.py) - 抖音签名生成

### FastAPI 相关（Coze 方案不需要）
以下文件仅用于 API 服务器，Coze 方案无需使用：
- `app/main.py` - FastAPI 入口
- `app/api/collect.py` - API 路由
- `app/services/apikey_validator.py` - API Key 验证
- `app/services/feishu_writer.py` - 飞书写入（Coze 直接使用飞书节点）

## 实施方案

### 阶段一：设计 Coze 工作流结构

需要创建 **4 个工作流模板**：

#### 模板 1：小红书博主笔记采集 ⭐

**工作流节点**：
```
开始节点
  ↓ (博主链接、Cookie、飞书授权码)
代码节点：采集博主笔记
  ↓ (返回 records 数组)
飞书多维表格：批量新增记录
  ↓
结束节点
```

**开始节点输入参数**：
- `bozhulianjie`（文本）：小红书博主主页 URL
- `cookie`（文本）：小红书 Cookie
- `maxNotes`（数字，默认 20）：最大采集数量

**飞书节点配置**（使用用户自己的授权码）：
- 在工作流设置中配置"PersonalBaseToken"环境变量
- 飞书节点使用该授权码写入

**代码节点**：整合采集逻辑并返回 records

#### 模板 2：小红书单条笔记采集

**工作流节点**：
```
开始节点
  ↓ (笔记链接、Cookie)
代码节点：采集单条笔记
  ↓
飞书多维表格：新增记录
  ↓
结束节点
```

**开始节点输入参数**：
- `bijilianjie`（文本）：笔记链接
- `cookie`（文本）

#### 模板 3：小红书博主信息采集

**工作流节点**：
```
开始节点
  ↓ (博主链接、Cookie)
代码节点：采集博主信息
  ↓
飞书多维表格：新增记录
  ↓
结束节点
```

#### 模板 4：抖音视频采集

类似模板 1，但用于抖音平台，采集博主视频数据。

### 阶段二：将 Python 代码适配为 Coze 代码节点

#### 关键改动点

1. **移除 FastAPI 和 async 依赖**
   - Coze 代码节点是同步函数
   - 将 `httpx.AsyncClient` 改为 `requests`
   - 移除所有 `async` 和 `await` 关键字

2. **简化输入参数获取**
   - 使用 `params` 对象获取输入
   - 示例：
     ```python
     cookie = params.cookie
     profile_url = params.bozhulianjie
     max_notes = params.maxNotes or 20
     ```

3. **返回格式调整**
   - 返回符合飞书多维表格的 `records` 数组
   - 每个 record 包含 `fields` 字段
   - 示例：
     ```python
     return {
         "records": [
             {
                 "fields": {
                     "笔记标题": "标题",
                     "笔记内容": "内容",
                     "点赞数": 123,
                 }
             }
         ]
     }
     ```

4. **依赖包限制**
   - 只能使用 Coze 支持的标准库：`requests`、`json`、`time`、`hashlib`、`urllib` 等
   - **execjs 问题**：Coze 不支持 `execjs`，需要将 JS 签名代码内嵌到 Python 代码中直接执行

#### 具体改造步骤

1. **创建目录结构**：
   ```
   小红书采集Fastapi方案/
   ├── coze_templates/           # 新建：Coze 模板目录
   │   ├── xhs_user_notes.py    # 博主笔记采集代码
   │   ├── xhs_single_note.py   # 单条笔记采集代码
   │   ├── xhs_profile_info.py  # 博主信息采集代码
   │   └── douyin_user_videos.py # 抖音视频采集代码
   ```

2. **重写采集代码**：
   - 从 `xhs_collector.py` 提取核心逻辑
   - 移除 class 结构，改为纯函数
   - 移除 async/await
   - 使用 requests 替代 httpx

3. **处理签名生成**：
   - 将 `xhs_sign.py` 中的 JS 代码内嵌到 Python
   - 或者使用纯 Python 实现签名算法（如果可行）

### 阶段三：创建用户文档

#### 1. Coze 工作流导入指南

创建文件：`docs/COZE_USER_GUIDE.md`

**内容结构**：

```markdown
# 小红书采集 Coze 工作流使用指南

## 一、导入工作流模板

### 方法 1：通过分享链接导入（推荐）
1. 打开分享链接：https://www.coze.cn/workflows/xxx
2. 点击"复制工作流"
3. 工作流自动添加到您的 Coze 空间

### 方法 2：通过 JSON 文件导入
1. 下载对应的工作流 JSON 文件
2. 在 Coze 中选择"导入工作流"
3. 上传 JSON 文件

## 二、配置 Cookie 和授权码

### 2.1 获取小红书 Cookie

1. 打开小红书网页版：https://www.xiaohongshu.com
2. 登录账号
3. 按 F12 打开开发者工具
4. 切换到 Network 标签
5. 刷新页面，找到任意请求
6. 在 Request Headers 中复制 Cookie 完整值

**Cookie 示例**：
```
a1=xxxxx; webId=xxxxx; web_session=xxxxx; ...
```

**注意事项**：
- Cookie 通常 7-30 天失效，需定期更新
- 建议使用小号，避免主账号风险

### 2.2 获取飞书多维表格授权码

1. 打开要写入的飞书多维表格
2. 点击右上角"..."菜单
3. 选择"获取授权码"
4. 复制 PersonalBaseToken

**授权码示例**：
```
pt-xxxxxxxxxxxxxxxxxxxxxx
```

**注意**：授权码永久有效，请勿公开传播。

## 三、使用工作流

### 场景 1：采集博主全部笔记

1. 运行"小红书博主笔记采集"工作流
2. 输入参数：
   - `博主主页链接`：https://www.xiaohongshu.com/user/profile/xxx
   - `cookie`：粘贴您的 Cookie
   - `最大采集数量`：20（可选，默认 20）
3. 在工作流设置中配置飞书授权码
4. 点击"运行"
5. 等待采集完成，数据自动写入飞书表格

### 场景 2：采集单条笔记

1. 运行"小红书单条笔记采集"工作流
2. 输入笔记链接和 Cookie
3. 点击"运行"

### 场景 3：采集博主信息

1. 运行"小红书博主信息采集"工作流
2. 输入博主主页链接和 Cookie
3. 点击"运行"

## 四、常见问题

### Q1: Cookie 失效怎么办？
A: 重新登录小红书，按上述步骤获取新的 Cookie。

### Q2: 采集失败率高怎么办？
A:
- 降低采集频率（减少 maxNotes）
- 更换 Cookie
- 检查网络连接

### Q3: 飞书写入失败？
A:
- 检查授权码是否正确
- 确认表格字段名称与代码一致
- 检查飞书表格权限

## 五、套餐说明

本工作流模板**完全免费**，用户可无限次使用。

如需技术支持，请联系客服。
```

#### 2. 创建多维表格字段说明文档

创建文件：`docs/FEISHU_TABLE_FIELDS.md`

列出所有字段名称、类型、说明，方便用户创建飞书表格。

### 阶段四：导出工作流模板文件

#### 创建工作流 JSON 文件

需要创建 4 个文件：
1. `coze_templates/小红书博主笔记采集.json`
2. `coze_templates/小红书单条笔记采集.json`
3. `coze_templates/小红书博主信息采集.json`
4. `coze_templates/抖音视频采集.json`

每个 JSON 文件包含：
- 工作流名称
- 节点配置（开始/代码/飞书/结束）
- 输入输出参数定义
- 代码节点的完整代码

### 阶段五：发布和分发

#### 分发方式

1. **GitHub 仓库**（推荐）
   - 创建独立的 GitHub 仓库
   - 包含所有模板 JSON 文件
   - 提供详细的 README 使用说明
   - 用户可以 star 和 fork

2. **Coze 平台分享**
   - 在 Coze 平台发布工作流
   - 生成分享链接
   - 用户一键复制工作流

3. **公众号/知识星球**
   - 提供下载链接
   - 附带视频教程
   - 持续更新优化

## 实施步骤总结

### 第一步：改造采集代码（核心）

1. 阅读 `xhs_collector.py` 源代码
2. 提取核心采集逻辑
3. 移除 async/await 和 FastAPI 依赖
4. 改为 Coze 代码节点格式
5. 测试代码是否能正常运行

**关键文件**：
- 源文件：[app/services/xhs_collector.py](../小红书采集Fastapi方案/app/services/xhs_collector.py)
- 新文件：`coze_templates/xhs_user_notes.py`

### 第二步：创建 Coze 工作流

1. 在 Coze 中创建新工作流
2. 添加节点（开始 → 代码 → 飞书 → 结束）
3. 配置输入输出参数
4. 粘贴改造后的代码到代码节点
5. 配置飞书节点（表格链接、字段映射）
6. 测试工作流运行

### 第三步：导出模板文件

1. 在 Coze 中导出工作流为 JSON
2. 保存到 `coze_templates/` 目录
3. 重复步骤 1-2，创建其他 3 个模板

### 第四步：编写用户文档

1. 创建 `docs/COZE_USER_GUIDE.md`
2. 创建 `docs/FEISHU_TABLE_FIELDS.md`
3. 录制视频教程（可选）

### 第五步：发布分发

1. 创建 GitHub 仓库
2. 上传所有模板和文档
3. 在 Coze 平台发布工作流
4. 生成分享链接
5. 推广给用户

## 关键文件路径

### 需要读取的源文件
- [app/services/xhs_collector.py](../小红书采集Fastapi方案/app/services/xhs_collector.py) - 小红书采集逻辑
- [app/services/xhs_sign.py](../小红书采集Fastapi方案/app/services/xhs_sign.py) - 签名生成
- [app/services/douyin_collector.py](../小红书采集Fastapi方案/app/services/douyin_collector.py) - 抖音采集逻辑

### 需要创建的文件
- `coze_templates/xhs_user_notes.py` - 博主笔记采集代码（Coze 版）
- `coze_templates/xhs_single_note.py` - 单条笔记采集代码（Coze 版）
- `coze_templates/xhs_profile_info.py` - 博主信息采集代码（Coze 版）
- `coze_templates/douyin_user_videos.py` - 抖音视频采集代码（Coze 版）
- `coze_templates/小红书博主笔记采集.json` - 工作流模板
- `coze_templates/小红书单条笔记采集.json` - 工作流模板
- `coze_templates/小红书博主信息采集.json` - 工作流模板
- `coze_templates/抖音视频采集.json` - 工作流模板
- `docs/COZE_USER_GUIDE.md` - 用户使用指南
- `docs/FEISHU_TABLE_FIELDS.md` - 飞书表格字段说明

## 验证计划

### 1. 代码改造验证
- [ ] 代码能在 Coze 代码节点中运行
- [ ] 能成功获取小红书数据
- [ ] 签名生成正常工作
- [ ] 返回的 records 格式正确

### 2. 工作流测试
- [ ] 输入参数正确传递到代码节点
- [ ] 代码节点输出能被飞书节点接收
- [ ] 数据成功写入飞书表格
- [ ] 字段类型匹配（数字、文本、日期等）

### 3. 用户体验测试
- [ ] 文档描述清晰易懂
- [ ] Cookie 获取步骤准确
- [ ] 授权码配置步骤准确
- [ ] 常见问题覆盖完整

### 4. 分发测试
- [ ] JSON 文件能成功导入 Coze
- [ ] 分享链接可正常访问
- [ ] 用户能一键复制工作流

## 优势分析

### vs API 服务器方案

| 对比项         | Coze 模板方案     | API 服务器方案      |
| -------------- | ----------------- | ------------------- |
| **服务器成本** | ¥0                | ¥300-500/年         |
| **技术门槛**   | 低（导入模板）    | 高（部署服务器）    |
| **维护成本**   | 低（更新模板）    | 高（服务器运维）    |
| **使用限制**   | 无限制            | 需要配额管理        |
| **数据安全**   | 用户自己的 Cookie | Cookie 需发给服务器 |
| **分发速度**   | 快（分享链接）    | 慢（需部署）        |

**结论**：Coze 模板方案在各方面都优于 API 服务器方案，特别适合免费分发给用户使用。
