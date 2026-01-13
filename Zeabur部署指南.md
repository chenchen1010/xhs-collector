# Zeabur 部署指南 - 小红书采集 API 服务

本指南提供两种 Zeabur 部署方式，均适合技术小白。

## 📋 方案对比

| 方案 | 适用场景 | 成本 | 难度 | 推荐度 |
|------|---------|------|------|--------|
| 方案A：Zeabur 云托管 | 没有服务器 | $5-10/月 | ⭐ | ⭐⭐⭐⭐ |
| 方案B：Zeabur + 阿里云 | 已有服务器 | 免费 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 方案A：Zeabur 云托管部署

### 适合人群
- 没有服务器
- 追求极简部署
- 可接受每月少量费用

### 部署步骤

#### 第1步：准备 GitHub 仓库（5分钟）

**1.1 创建 GitHub 账号**（如已有则跳过）
- 访问 https://github.com
- 点击 Sign up 注册

**1.2 创建新仓库**
1. 登录 GitHub
2. 点击右上角 `+` → `New repository`
3. Repository name：`xhs-collector`（随意命名）
4. 选择 `Public`（公开）
5. 点击 `Create repository`

**1.3 上传代码到 GitHub**

在本地项目目录执行：

```bash
cd "/Users/burning/Desktop/Code/Coze代码开发/小红书采集Fastapi方案"

# 初始化 Git
git init
git add .
git commit -m "Initial commit"

# 关联远程仓库（替换成你的仓库地址）
git remote add origin https://github.com/你的用户名/xhs-collector.git
git branch -M main
git push -u origin main
```

如果不熟悉命令行，可以使用 GitHub Desktop（图形化工具）：
- 下载：https://desktop.github.com
- 拖拽文件夹到 GitHub Desktop
- 点击 Publish 上传

---

#### 第2步：注册并登录 Zeabur（2分钟）

1. 访问 https://zeabur.com
2. 点击右上角 `Login`
3. 选择 `Continue with GitHub`（用 GitHub 账号登录，最方便）
4. 授权 Zeabur 访问你的 GitHub

---

#### 第3步：创建项目并导入仓库（3分钟）

**3.1 创建新项目**
1. 登录 Zeabur 后，点击 `Create Project`
2. Project Name：`xhs-collector`（随意命名）
3. Region：选择 `Hong Kong`（离国内最近，速度快）
4. 点击 `Create`

**3.2 导入 GitHub 仓库**
1. 在项目页面，点击 `Add Service`
2. 选择 `Git`
3. 选择 `Import from GitHub`
4. 找到你刚才创建的仓库 `xhs-collector`
5. 点击仓库名称导入

Zeabur 会自动检测到这是 Python FastAPI 项目，并开始部署。

---

#### 第4步：配置环境变量（2分钟）

**4.1 进入环境变量设置**
1. 在项目页面，点击你的服务名
2. 切换到 `Variables` 标签
3. 点击 `Add Variable`

**4.2 添加必需的环境变量**

添加以下环境变量：

| Key | Value | 说明 |
|-----|-------|------|
| `XHS_COOKIE` | 你的Cookie值 | 从浏览器获取（见下方教程） |
| `PORT` | `8080` | 服务端口（可选，Zeabur会自动设置） |

**如何获取 Cookie：**

1. 浏览器打开 www.xiaohongshu.com
2. 按 F12 打开开发者工具
3. 切换到 Network (网络) 标签
4. 刷新页面
5. 点击任意请求 → Request Headers
6. 找到 `Cookie:`，复制整行值
7. 粘贴到 Zeabur 的 `XHS_COOKIE` 变量中

**4.3 保存配置**
- 点击 `Save`
- Zeabur 会自动重新部署服务

---

#### 第5步：等待部署完成（2-5分钟）

**部署过程：**
1. Building（构建中）：安装依赖
2. Deploying（部署中）：启动服务
3. Running（运行中）：部署成功 ✅

**查看部署日志：**
- 点击服务卡片 → `Logs` 标签
- 看到 `Application startup complete` 表示成功

---

#### 第6步：获取访问地址并测试（1分钟）

**6.1 生成公开域名**
1. 点击服务卡片 → `Networking` 标签
2. 点击 `Generate Domain`
3. Zeabur 会自动分配一个域名，如：`xhs-collector-xxx.zeabur.app`
4. 复制域名

**6.2 测试 API**
浏览器访问：
```
https://xhs-collector-xxx.zeabur.app/docs
```

看到 Swagger API 文档页面 = 部署成功！🎉

---

#### 第7步：在 Coze 中使用（2分钟）

在 Coze 工作流中添加 HTTP 请求节点：

**采集单篇笔记：**
- 请求方式：`POST`
- URL：`https://xhs-collector-xxx.zeabur.app/api/note/single`
- Headers：
  ```
  Content-Type: application/json
  ```
- Body（JSON）：
  ```json
  {
    "note_url": "{{input.笔记链接}}"
  }
  ```

**响应数据格式：**
```json
{
  "records": [
    {
      "fields": {
        "笔记标题": "...",
        "笔记内容": "...",
        "点赞数": 123,
        ...
      }
    }
  ]
}
```

直接用代码节点提取 `records` 字段，写入飞书多维表格即可。

---

### 成本说明

**Zeabur 定价：**
- 免费额度：每月 $5 免费额度（约35元）
- 超出计费：约 $0.05/小时（0.35元/小时）

**预估成本（你的场景）：**
- 每天采集 10-50 次
- 每月成本：**$0-3（0-20元）**
- 如果使用量很少，完全在免费额度内

---

## 方案B：Zeabur + 阿里云服务器

### 适合人群
- 已有阿里云服务器
- 希望零额外费用
- 想要可视化管理

### 优势
✅ 成本：0元/月（使用现有服务器）
✅ 管理：Zeabur 可视化控制台
✅ 部署：一键部署，自动更新
✅ 安全：自动 HTTPS 证书

---

### 部署步骤

#### 第1步：准备阿里云服务器（5分钟）

**1.1 确保服务器可 SSH 连接**
测试连接：
```bash
ssh root@你的服务器IP
# 输入密码，能登录即可
```

**1.2 配置安全组规则**
在阿里云控制台 → ECS → 安全组 → 添加规则：

| 端口 | 说明 |
|------|------|
| 22 | SSH（Zeabur 需要） |
| 80 | HTTP |
| 443 | HTTPS |

---

#### 第2步：在 Zeabur 添加服务器（3分钟）

**2.1 进入服务器管理**
1. 登录 Zeabur 控制台
2. 点击左侧菜单 `Servers`
3. 点击 `Add Server`

**2.2 填写服务器信息**

| 字段 | 值 | 说明 |
|------|---|------|
| Server Name | 阿里云服务器 | 随意命名 |
| Host | 你的服务器IP | 公网IP地址 |
| Port | 22 | SSH端口 |
| Username | root | 或其他有sudo权限的用户 |
| Authentication | Password | 选择认证方式 |
| Password | 你的root密码 | 服务器密码 |

**2.3 测试连接**
- 点击 `Test Connection`
- 显示 ✅ Connected 表示成功

**2.4 保存**
- 点击 `Add Server`

---

#### 第3步：部署项目到你的服务器（按方案A的步骤）

**3.1 准备 GitHub 仓库**
参考方案A的第1步上传代码到 GitHub

**3.2 创建项目并导入**
1. 点击 `Create Project`
2. 点击 `Add Service` → `Git`
3. 选择你的 GitHub 仓库

**3.3 选择部署目标（重点！）**
- **关键步骤**：在部署设置中
- 找到 `Deploy to` 选项
- 选择 `阿里云服务器`（你刚才添加的）
- Zeabur 会将服务部署到你的服务器上

**3.4 配置环境变量**
添加 `XHS_COOKIE` 环境变量（同方案A第4步）

**3.5 部署**
点击 `Deploy`，等待 3-5 分钟

---

#### 第4步：获取域名并测试

Zeabur 会自动配置：
- 反向代理
- HTTPS 证书
- 域名绑定

你会得到一个 `.zeabur.app` 域名，访问测试即可。

---

### 与纯阿里云部署对比

| 特性 | Zeabur + 阿里云 | 纯阿里云手动部署 |
|------|-----------------|-----------------|
| 部署难度 | ⭐⭐（点几下） | ⭐⭐⭐⭐（敲命令） |
| HTTPS配置 | ✅ 自动 | ❌ 需手动配置证书 |
| 日志查看 | ✅ 网页查看 | ❌ SSH查看 |
| 代码更新 | ✅ Git push自动部署 | ❌ 手动上传+重启 |
| 成本 | 💰 免费 | 💰 免费 |

---

## 🎯 部署后检查清单

部署完成后，逐项检查：

- [ ] 访问 `/docs` 能看到 API 文档
- [ ] 在 Swagger 页面测试一个接口（如采集单篇笔记）
- [ ] 检查日志是否有报错
- [ ] 在 Coze 中配置 HTTP 节点测试
- [ ] 确认能成功写入飞书多维表格

---

## 🔧 常见问题

### Q1: 部署失败，显示 "Build failed"
**A:** 检查以下几点：
1. `requirements.txt` 文件是否存在
2. `zbpack.json` 配置是否正确
3. 查看构建日志具体错误信息

### Q2: API 返回 406 错误
**A:** Cookie 失效了，需要重新获取并更新环境变量。

### Q3: Zeabur 如何更新 Cookie？
**A:**
1. 进入项目 → 点击服务 → Variables 标签
2. 修改 `XHS_COOKIE` 的值
3. 点击 Save，服务会自动重启

### Q4: 如何查看服务日志？
**A:**
1. 进入项目 → 点击服务
2. 切换到 `Logs` 标签
3. 实时查看运行日志

### Q5: 可以绑定自己的域名吗？
**A:** 可以！
1. 在 Zeabur 服务设置中 → `Networking` 标签
2. 点击 `Add Domain`
3. 输入你的域名（需要先在域名注册商处添加 CNAME 记录）

### Q6: Zeabur 服务如何停止？
**A:**
1. 进入项目 → 点击服务卡片
2. 点击右上角 `...` → `Pause Service`
3. 暂停期间不计费

### Q7: 方案B（自己服务器）还能用 SSH 管理服务器吗？
**A:** 可以！Zeabur 只是帮你部署和管理服务，不影响你的其他操作。

---

## 📞 获取帮助

如遇到问题：

1. **查看日志**：Zeabur 控制台 → Logs
2. **Zeabur 文档**：https://zeabur.com/docs
3. **Zeabur Discord**：https://discord.gg/zeabur
4. **本项目 Issues**：提交 GitHub Issue

---

## 🎉 总结

**推荐方案：**
- 有阿里云服务器 → 选方案B（Zeabur + 阿里云）
- 没有服务器 → 选方案A（Zeabur 云托管）

**预计总用时：**
- 方案A：15-20分钟
- 方案B：20-30分钟

**部署成功标志：**
- 浏览器能访问 `https://your-app.zeabur.app/docs`
- Coze HTTP 节点能成功调用 API
- 数据能正常写入飞书多维表格

祝部署顺利！🚀
