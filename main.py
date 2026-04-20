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
            
            # 3. 终极探测：穿透代理，尝试全局和私有属性
            if not mgr:
                # 尝试 A: 从 __dict__ 寻找隐藏的实例引用 (穿透 Proxy)
                ctx_dict = getattr(self.context, "__dict__", {})
                for k, v in ctx_dict.items():
                    if k.endswith("context") or k.endswith("inst"):
                        logger.info(f"Pierced proxy! Found hidden ref: {k}")
                        mgr = getattr(v, "message_manager", None) or getattr(v, "message_mgr", None)
                        if mgr: break
                
                # 尝试 B: 全局单例模式 (AstrBot 核心)
                if not mgr:
                    try:
                        from astrbot.core.instance import AstrBot
                        bot_inst = AstrBot.get_instance()
                        if bot_inst:
                            mgr = getattr(bot_inst, "message_manager", None) or getattr(bot_inst, "message_mgr", None)
                            if mgr: logger.info("Accessed history via GLOBAL singleton!")
                    except: pass

                # 尝试 C: 从 event 对象再次寻找 (Session ID 查找)
                if not mgr:
                    for key in ["session", "history", "message_mgr"]:
                        mgr = getattr(event, key, None)
                        if mgr: break
            
            content = None
            if mgr:
                # 首先确保 mgr 有获取消息的能力
                fetcher = getattr(mgr, "get_messages", None) or getattr(mgr, "get_history", None)
                
                # 如果 mgr 是 session 却没方法，尝试去它的提供者 (Provider) 找
                if not fetcher:
                    provider = getattr(mgr, "provider", None)
                    if provider:
                        fetcher = getattr(provider, "get_messages", None)
                        mgr = provider # 切换 mgr 到提供者
                
                msgs = []
                try:
                    # 尝试 A: 带参数调用
                    try: msgs = await fetcher(session_id=session_id, limit=10)
                    except: pass
                    
                    # 尝试 B: 不带参数调用 (session 对象本身的 get_messages 往往不需要 ID)
                    if not msgs:
                        try: msgs = await fetcher(limit=10)
                        except: pass
                        
                    # 尝试 C: 直接翻属性 (很多框架直接存成列表)
                    if not msgs:
                        for attr in ["messages", "_messages", "history_list"]:
                            val = getattr(mgr, attr, None)
                            if isinstance(val, list):
                                msgs = val
                                logger.info(f"Stepped into attribute: {attr}")
                                break
                    
                    # 尝试 D: 针对 Dataclass (MessageSession) 的深挖
                    if not msgs:
                        # 看看有没有 history 属性
                        hist = getattr(mgr, "history", None)
                        if hist:
                            logger.info("Deep focus: Found 'history' on session object.")
                            msgs = getattr(hist, "messages", []) or []
                            if not msgs and hasattr(hist, "get_messages"):
                                try: msgs = await hist.get_messages(limit=10)
                                except: pass
                    
                    if not msgs:
                        # 打印所有非内置属性，让我们看个明白
                        all_attrs = [a for a in dir(mgr) if not a.startswith("__")]
                        logger.info(f"Manager Attributes Hunt: {all_attrs}")

                    logger.info(f"History Result: Found {len(msgs)} potential nodes.")
                    for m in reversed(msgs):
                        text = getattr(m, "content", getattr(m, "text", getattr(m, "raw_message", "")))
                        # 识别回复角色
                        role = str(getattr(m, "role", "") or getattr(m, "type", "")).lower()
                        user = str(getattr(m, "sender_id", "") or getattr(m, "user_id", ""))
                        
                        # 避开指令，寻找机器人的干货
                        if role in ["assistant", "bot", "1", "reply"] or (user and user != str(event.user_id)):
                            # 简单的文本过滤
                            if text and (len(text) > 5) and not text.strip().startswith("/"):
                                content = text
                                logger.info(f"JACKPOT! Captured bot message (len={len(text)})")
                                break
                except Exception as e:
                    logger.warning(f"Extreme rescue failed: {e}")
            
            if not content:
                logger.error("Capture capture FAILED: No content found in history.")
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
