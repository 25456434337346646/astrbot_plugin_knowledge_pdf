"""AstrBot plugin to export knowledge base entries as PDF.
"""

import os
import uuid
import asyncio
from pathlib import Path

from fpdf import FPDF
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, File
from astrbot.api import logger


async def fetch_content(context: Context, key: str) -> str | None:
    """Retrieve knowledge base content via Tool Proxy with deep safety."""
    try:
        # Securely find tool manager
        inst = getattr(context, "inst", None)
        manager = getattr(context, "tool_manager", None)
        if not manager and inst:
            manager = getattr(inst, "tool_manager", None)
            
        if manager:
            tools = getattr(manager, "tools", {})
            if "astr_kb_search" in tools:
                tool = tools["astr_kb_search"]
                func = getattr(tool, "func", None) or getattr(tool, "call", None)
                if func:
                    res = await func(query=key)
                    if res: return str(res)
        
        # Fallback to direct invoke on context
        if hasattr(context, "invoke_tool"):
            res = await context.invoke_tool("astr_kb_search", {"query": key})
            if res: return str(res)
    except Exception as exc:
        logger.warning(f"KB search failed: {exc}")
    return None


def render_pdf(content: str, output_path: Path) -> None:
    """Render content to PDF with font fallback."""
    pdf = FPDF()
    pdf.add_page()
    
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    
    font_loaded = False
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdf.add_font("Chinese", "", fp)
                pdf.set_font("Chinese", size=11)
                font_loaded = True
                break
            except Exception: continue
    
    if not font_loaded:
        pdf.set_font("Helvetica", size=12)

    pdf.set_auto_page_break(auto=True, margin=15)
    for line in content.splitlines():
        pdf.multi_cell(0, 8, txt=line, align="L")
    pdf.output(str(output_path))


@register("knowledge_pdf", "Master", "极简 PDF 导出器", "1.1.1")
class KnowledgePDFPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("pdf")
    async def pdf_smart(self, event: AstrMessageEvent) -> MessageEventResult:
        """智能化 PDF 指令：安全加固版。"""
        args = event.message_str.strip().split(maxsplit=1)
        
        if len(args) > 1:
            # 模式 A：搜索知识库
            key = args[1].strip()
            logger.info(f"Target: Search KB for '{key}'")
            content = await fetch_content(self.context, key)
            if not content:
                return event.plain_result(f"未能在知识库中搜到关于 `{key}` 的内容。")
            filename = f"Knowledge_{key}.pdf"
        else:
            # 模式 B：捕捉上一条回复
            logger.info("Target: Capture last bot message")
            session_id = event.session_id
            
            # 安全寻找消息管理器
            inst = getattr(self.context, "inst", None)
            mgr = getattr(self.context, "message_manager", None)
            if not mgr and inst:
                mgr = getattr(inst, "message_manager", None)
            
            content = None
            if mgr and hasattr(mgr, "get_messages"):
                try:
                    msgs = await mgr.get_messages(session_id=session_id, limit=5)
                    logger.info(f"Retrieved {len(msgs)} messages from history.")
                    
                    for m in reversed(msgs):
                        # 调试日志：打印每条消息的特征
                        role = str(getattr(m, "role", "")).lower()
                        sender = str(getattr(m, "sender_id", ""))
                        text = getattr(m, "content", "")
                        logger.info(f"Tracing msg: role={role}, sender={sender}, len={len(text)}")
                        
                        # 广谱识别：只要不是用户发的消息，且有内容，就视为机器人回复
                        # 或者 role 是 assistant/bot
                        if role in ["assistant", "bot", "1", "system"] or (sender and sender != str(event.user_id)):
                            if text and not text.startswith("/"): # 避开指令本身
                                content = text
                                logger.info("Found match for bot message!")
                                break
                except Exception as e:
                    logger.warning(f"Failed to fetch messages: {e}")
            
            if not content:
                return event.plain_result("未能捕捉到对话内容，请先检索一次知识库。")
            filename = "Captured_Conversation.pdf"

        # 生成与发送
        tmp_path = Path("/tmp") / f"pdf_{uuid.uuid4().hex}.pdf"
        try:
            render_pdf(content, tmp_path)
            # 再次确认路径权限
            if not os.path.exists(tmp_path):
                raise FileNotFoundError("PDF file was not created.")
            return event.file_result(str(tmp_path), filename)
        except Exception as exc:
            logger.error(f"PDF Error: {exc}")
            return event.plain_result(f"生成失败: {exc}")
