# Coze 方案（小红书）

这里先放 **单条笔记采集** 的 Coze 代码节点模板。

## 文件说明

- `xhs_single_note.py`：代码节点完整代码（复制到 Coze 代码节点即可用）

## 使用超简版步骤

1. 在 Coze 新建工作流，节点顺序：开始 → 代码 → 飞书多维表格 → 结束
2. 代码节点里选择 Python，把 `xhs_single_note.py` 的内容全部粘进去
3. 开始节点输入两个参数：
   - `bijilianjie`（笔记链接）
   - `cookie`（小红书 Cookie）
4. 代码节点输出 `records`，飞书节点用“自动映射”写入表格

更详细的图文说明可看：`docs/小红书单条笔记采集-Coze使用指南.md`
