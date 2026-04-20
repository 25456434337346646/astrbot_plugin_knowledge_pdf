# Changelog

All notable changes to this project will be documented in this file.

## [1.2.6] - 2026-04-20

### Fixed
- **终极发送适配**：手动实例化 `MessageEventResult` 并显式设置 `.chain` 属性，彻底解决了在 AstrBot V3 部分版本（如 OneBot/aiocqhttp）中由于构造函数参数 `message_chain` 不匹配导致的运行时崩溃。
- **环境隔离一致性**：同步了多处物理路径副本，确保更新能覆盖所有潜在的脚本副本。

## [1.2.5] - 2026-04-20

### Fixed
- **渲染安全增强**：引入智能 Base64 截断与 XML 非法字符转义处理，防止公式中含有的特殊符号导致 PDF 生成失败。
- **鲁棒性补丁**：为 Paragraph 渲染添加容错块，确保在字符损坏时依然能产出文档。

## [1.2.1] - 2026-04-20

### Added
- **渲染引擎迁移**：全面迁移至 ReportLab Platypus，支持精美排版设计。
- **深度内核集成**：直接调用 `kb_manager` 实现会话感知的知识库检索。
- **字体本地化**：支持 macOS (STHeiti) 与 Linux (NotoSans) 中文字体注册。

---

## [1.1.0] - 2026-04-18
- 实现基础 PDF 导出功能。
