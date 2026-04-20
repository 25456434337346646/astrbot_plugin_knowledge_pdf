# AstrBot Knowledge PDF Exporter

一款为 AstrBot 设计的极简 PDF 导出插件，完美支持中文渲染与语义检索。

## ✨ 特色功能

1. **智能命令 (/pdf)**:
   - **无参数模式**: 直接输入 `/pdf`，插件将自动捕捉机器人刚才说的最后一段话并生成 PDF。适合在 AI 检索完知识库后快速备份。
   - **搜索模式**: 输入 `/pdf <关键词>`，插件将利用 AstrBot 核心检索能力搜索知识库并导出最优结果。
2. **环境自适应**: 自动探测 macOS 和 Linux 系统的中文字体，彻底解决 PDF 乱码问题。
3. **轻量抗造**: 不依赖 Playwright 等笨重的无头浏览器，秒级生成，适合低配服务器。

## 🚀 安装方法

在 AstrBot WebUI 的插件管理中，点击“从 GitHub 安装”，输入链接：
`https://github.com/25456434337346646/astrbot_plugin_knowledge_pdf`

## 🛠️ 配合多模态路由使用建议

建议在使用多模态路由插件进行知识库检索后，直接跟一句 `/pdf`，即可获得精美的本地 PDF 存档。

---
*Created by Master & Anti-Gravity Assistant*
