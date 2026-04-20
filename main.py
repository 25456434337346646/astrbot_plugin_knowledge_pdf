"""AstrBot plugin to export knowledge base entries as PDF using ReportLab.
Advanced version: Deeply integrated with AstrBot Knowledge Base Core.
"""

import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

# ReportLab libraries
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, grey

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

class KnowledgePDFPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.font_name = "Helvetica" # Default fallback
        self._setup_fonts()

    def _setup_fonts(self):
        """Register Chinese fonts for macOS and Linux."""
        font_candidates = [
            ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti-Light"),
            ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
            ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK"),
            ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "WQY-MicroHei"),
        ]
        
        for path, name in font_candidates:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    self.font_name = name
                    logger.info(f"Registered font: {name} from {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to register font {name}: {e}")
        
    def _get_styles(self):
        """Create PDF styles."""
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=black,
            fontName=self.font_name
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            fontName=self.font_name
        )
        footer_style = ParagraphStyle(
            'CustomFooter',
            parent=styles['Normal'],
            fontSize=9,
            textColor=grey,
            alignment=1,
            fontName=self.font_name
        )
        return {'title': title_style, 'body': body_style, 'footer': footer_style}

    async def fetch_kb_content(self, query: str, event: AstrMessageEvent) -> str | None:
        """Deeply integrated retrieval logic mirroring AstrBot core."""
        try:
            kb_mgr = getattr(self.context, "kb_manager", None)
            if not kb_mgr:
                logger.warning("Knowledge Base Manager (kb_manager) not found in Context.")
                return None

            umo = event.unified_msg_origin
            # Get config mirroring core logic
            config = self.context.get_config(umo=umo) if hasattr(self.context, "get_config") else {}
            
            # Simplified version of core/tools/knowledge_base_tools.py:retrieve_knowledge_base
            kb_names = config.get("kb_names", [])
            top_k = config.get("kb_final_top_k", 5)
            top_k_fusion = config.get("kb_fusion_top_k", 20)

            if not kb_names:
                logger.debug("No knowledge bases configured for this session.")
                return None

            logger.debug(f"[Export] Starting KB retrieval: {kb_names}, query='{query}'")
            
            # Direct call to kb_manager.retrieve
            kb_context = await kb_mgr.retrieve(
                query=query,
                kb_names=kb_names,
                top_k_fusion=top_k_fusion,
                top_m_final=top_k,
            )
            
            if not kb_context: return None
            
            formatted = kb_context.get("context_text", "")
            if formatted:
                results = kb_context.get("results", [])
                logger.info(f"[Export] Retrieved {len(results)} chunks for PDF.")
                return formatted
                
        except Exception as exc:
            logger.error(f"Deep KB retrieval failed: {exc}", exc_info=True)
        return None

    async def capture_history_content(self, event: AstrMessageEvent) -> str | None:
        """Capture last bot response with proxy piercing."""
        session_id = event.session_id
        mgr = getattr(self.context, "message_manager", None)
        
        if not mgr:
            # Pierce: check hidden references (Proxy bypass)
            ctx_dict = getattr(self.context, "__dict__", {})
            for v in ctx_dict.values():
                if hasattr(v, "message_manager"):
                    mgr = v.message_manager; break
            
            if not mgr:
                try:
                    from astrbot.core.instance import AstrBot
                    bot_inst = AstrBot.get_instance()
                    if bot_inst: mgr = bot_inst.message_manager
                except: pass

        if not mgr: return None

        try:
            fetcher = getattr(mgr, "get_messages", None) or getattr(mgr, "get_history", None)
            msgs = []
            if fetcher:
                try: msgs = await fetcher(session_id=session_id, limit=15)
                except: 
                    try: msgs = await fetcher(limit=15)
                    except: pass
            
            if not msgs:
                for attr in ["messages", "_messages", "history_list"]:
                    val = getattr(mgr, attr, None)
                    if isinstance(val, list):
                        msgs = val; break

            for m in reversed(msgs):
                text = str(getattr(m, "content", getattr(m, "text", "")))
                role = str(getattr(m, "role", getattr(m, "type", ""))).lower()
                user = str(getattr(m, "sender_id", getattr(m, "user_id", "")))
                
                if role in ["assistant", "bot", "reply"] or (user and user != str(event.user_id)):
                    if text and len(text.strip()) > 10 and not text.strip().startswith("/"):
                        return text
        except Exception as e:
            logger.warning(f"History capture failed: {e}")
        return None

    def render_pdf(self, content: str, title_text: str, output_path: Path):
        """Render to PDF using ReportLab Platypus."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
        )
        
        styles = self._get_styles()
        story = []
        
        # Header
        story.append(Paragraph(title_text, styles['title']))
        story.append(Spacer(1, 12))
        
        # Meta
        meta_info = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(meta_info, styles['footer']))
        story.append(Spacer(1, 24))
        
        # Content
        lines = content.split('\n')
        for line in lines:
            if not line.strip():
                story.append(Spacer(1, 6))
                continue
            clean_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(clean_line, styles['body']))
        
        # Footer
        story.append(Spacer(1, 48))
        story.append(Paragraph("--- Generated by AstrBot (Deep KB Integrated) ---", styles['footer']))
        
        doc.build(story)

    @filter.command("pdf")
    async def pdf_handle(self, event: AstrMessageEvent) -> MessageEventResult:
        """Unified /pdf handler."""
        args = event.message_str.strip().split(maxsplit=1)
        
        if len(args) > 1:
            query = args[1].strip()
            content = await self.fetch_kb_content(query, event)
            if not content:
                return event.plain_result(f"未能在知识库中搜到关于 `{query}` 的内容，请确认已绑定知识库并包含相关内容。")
            title = f"知识库查询结果: {query}"
            filename = f"Knowledge_{query}.pdf"
        else:
            content = await self.capture_history_content(event)
            if not content:
                return event.plain_result("未能识别到可导出的回复内容。请尝试 `/pdf 关键词` 检索知识库。")
            title = "对话内容导出"
            filename = "Captured_Conversation.pdf"

        tmp_path = Path("/tmp") / f"pdf_{uuid.uuid4().hex}.pdf"
        try:
            self.render_pdf(content, title, tmp_path)
            return event.file_result(str(tmp_path), filename)
        except Exception as e:
            logger.error(f"Render PDF Error: {e}")
            return event.plain_result(f"PDF 生成失败: {str(e)}")

@register("knowledge_pdf", "Master", "专业级知识库导出器", "1.2.1")
def plugin_entry(context: Context):
    return KnowledgePDFPlugin(context)
