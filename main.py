"""AstrBot plugin to export knowledge base entries as PDF.

The plugin defines a command ``/knowledgepdf <key>``. It attempts to retrieve the
knowledge base entry identified by ``key`` and renders the plain‑text content to a
PDF file using the *fpdf2* library. The resulting PDF is sent back to the user via
``event.file_result``.

The implementation makes a few reasonable assumptions about the AstrBot API:

* ``Context`` provides a ``knowledge_base`` attribute exposing a ``get(key)`` method
  that returns a string with the entry's content. If the key is not found, a
  ``None`` is returned.
* ``event`` (an ``AstrMessageEvent``) supports ``file_result(path, filename)`` to
  send a file back to the user.

If the actual API differs, the user can adjust the ``fetch_content`` helper to
match their environment.
"""

import os
import uuid
from pathlib import Path

from fpdf import FPDF

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


async def fetch_content(context: Context, key: str) -> str | None:
    """Retrieve knowledge base content for *key*.

    1. Attempts direct lookup.
    2. Falls back to semantic search with enhanced logging.
    """
    # Final Strategy – Tool Proxy (The most robust way)
    try:
        logger.info(f"Attempting to invoke tool 'astr_kb_search' for '{key}'...")
        # Try to find the tool manager or use the context's tool caller
        manager = getattr(context, "tool_manager", None) or getattr(getattr(context, "inst", None), "tool_manager", None)
        if manager:
            # result = await manager.invoke_tool("astr_kb_search", {"query": key})
            # Some versions use a different invocation pattern
            tools = getattr(manager, "tools", {})
            if "astr_kb_search" in tools:
                tool = tools["astr_kb_search"]
                func = getattr(tool, "func", None)
                if func:
                    logger.info("Found 'astr_kb_search' tool. Calling it...")
                    res = await func(query=key)
                    if res:
                        # The tool usually returns a string with "Sources:" etc.
                        return str(res)
    except Exception as exc:
        logger.warning(f"Tool proxy invocation failed: {exc}")

    return None


def render_pdf(content: str, output_path: Path) -> None:
    """Render *content* to a simple PDF saved at *output_path*.

    Attempts to load a Chinese-compatible font to ensure text visibility.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Try to find a Chinese font
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux (Debian/Ubuntu)
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",  # Linux (CentOS/Fedora)
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
    ]
    
    font_loaded = False
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdf.add_font("Chinese", "", fp)
                pdf.set_font("Chinese", size=11)
                font_loaded = True
                break
            except Exception:
                continue
    
    if not font_loaded:
        logger.warning("No Chinese font found, falling back to Helvetica (Chinese text may be broken)")
        pdf.set_font("Helvetica", size=12)

    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Split content into lines, add them one by one.
    for line in content.splitlines():
        # multi_cell is better for long lines to avoid overflow
        pdf.multi_cell(0, 8, txt=line, align="L")
    pdf.output(str(output_path))


@register("knowledge_pdf", "Master", "从知识库导出 PDF", "1.0.0")
class KnowledgePDFPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("knowledge_pdf")
    async def knowledgepdf(self, event: AstrMessageEvent) -> MessageEventResult:
        """Handle the ``/knowledgepdf <key>`` command.

        The command expects a single argument – the identifier of the knowledge
        base entry. It returns a PDF file if the entry exists, otherwise a text
        message explaining the failure.
        """
        args = event.message_str.strip().split(maxsplit=1)
        if len(args) < 2:
            return event.plain_result("Usage: /knowledgepdf <entry_key>")

        key = args[1].strip()
        logger.info(f"Generating PDF for knowledge key: {key}")
        content = await fetch_content(self.context, key)
        if not content:
            return event.plain_result(f"未找到知识条目 `{key}`，请检查键名或确保知识库已配置。")

        # Create a temporary PDF file – use UUID to avoid collisions.
        tmp_dir = Path("/tmp")
        pdf_path = tmp_dir / f"knowledge_{key}_{uuid.uuid4().hex}.pdf"
        try:
            render_pdf(content, pdf_path)
        except Exception as exc:  # pragma: no cover – unlikely with fpdf2
            logger.error(f"PDF generation failed for {key}: {exc}")
            return event.plain_result("生成 PDF 失败，请稍后再试。")

        # Send the file back to the user.
        filename = f"{key}.pdf"
        return event.file_result(str(pdf_path), filename)
