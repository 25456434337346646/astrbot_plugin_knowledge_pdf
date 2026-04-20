# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2026-04-20

### Added
- **深度内核集成**：直接对接 AstrBot `kb_manager`，替代了此前的间接工具调用方式。
- **UMO 感知**：支持根据当前会话的 `unified_msg_origin` 自动匹配知识库配置。
- **macOS 字体适配**：自动探测并注册 `STHeiti` (华文细黑) 字体，彻底修复 macOS 预览 PDF 时的乱码问题。

### Changed
- **渲染引擎迁移**：从 `fpdf2` 全面迁移至 **ReportLab Platypus**。
- **排版优化**：实现了基于段落（Paragraph）的布局，支持自动换行与行间距精确控制。
- **元数据升级**：更新版本号至 1.2.1。

### Fixed
- **XML 字符干扰**：修复了在 PDF 渲染时因特殊字符（如 `<` `>` `&`）导致的解析错误。
- **代理穿透**：优化了历史记录捕获逻辑，在 `Proxy` 拦截环境下仍能稳定获取回复内容。

---

## [1.1.0] - 2026-04-18

### Added
- 实现基础 PDF 导出功能。
- 支持 `/pdf` 指令捕捉机器人回复。
- 支持 `/pdf <关键词>` 调用知识库工具。
