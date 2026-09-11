import html
from typing import List
from b2b_digest.models import DailyDigest, DigestItem, PriorityLevel


def _get_priority_badge(priority: PriorityLevel) -> str:
    if priority == PriorityLevel.ALTA:
        return "🔴 ALTA"
    elif priority == PriorityLevel.MEDIA:
        return "🟡 MEDIA"
    return "🟢 BASSA"


def format_to_html(digest: DailyDigest) -> str:
    """Format DailyDigest into Telegram-compliant HTML markup.
    
    Telegram HTML strictly supports: <b>, <strong>, <i>, <em>, <u>, <ins>,
    <s>, <strike>, <del>, <span>, <a href="...">, <code>, <pre>.
    All user strings are safely escaped with html.escape to prevent malformed tag errors.
    """
    lines: List[str] = []

    # Header
    lines.append(f"📊 <b>B2B DIGEST INTELLIGENCE — {html.escape(digest.date)}</b>\n")
    lines.append(f"<i>{html.escape(digest.executive_summary)}</i>\n")
    lines.append(f"📌 <b>Opportunità rilevate:</b> {digest.total_items_analyzed}\n")
    lines.append("━" * 28 + "\n")

    if not digest.items:
        lines.append("<i>Nessuna nuova opportunità identificata per oggi.</i>")
        return "\n".join(lines)

    for idx, item in enumerate(digest.items, 1):
        safe_title = html.escape(item.title)
        badge = _get_priority_badge(item.priority)
        category_label = html.escape(item.category.value.replace("_", " "))

        lines.append(f"<b>{idx}. {safe_title}</b>")
        lines.append(f"🏷 <i>[{category_label}]</i> | Priorità: <b>{badge}</b>")

        if item.issuer:
            lines.append(f"🏛 <b>Ente:</b> {html.escape(item.issuer)}")
        if item.importo_o_agevolazione and item.importo_o_agevolazione.lower() not in ("n/d", "none", ""):
            lines.append(f"💰 <b>Importo/Agevolazione:</b> {html.escape(item.importo_o_agevolazione)}")
        if item.data_scadenza and item.data_scadenza.lower() not in ("n/d", "none", ""):
            lines.append(f"⏰ <b>Scadenza:</b> {html.escape(item.data_scadenza)}")

        lines.append(f"🎯 <b>Target:</b> {html.escape(item.target_audience)}")

        lines.append("📋 <b>Punti chiave:</b>")
        for point in item.key_takeaways:
            lines.append(f"  • {html.escape(point)}")

        if item.actionable_step:
            lines.append(f"⚡ <b>Azione consigliata:</b> {html.escape(item.actionable_step)}")

        safe_url = html.escape(item.original_url, quote=True)
        lines.append(f"🔗 <a href=\"{safe_url}\"><b>Apri bando / fonte ufficiale</b></a>")
        lines.append("")

    lines.append("🤖 <i>Elaborato automaticamente da B2B Digest Agent con Google Gemini Pro</i>")
    return "\n".join(lines)


def format_to_markdown(digest: DailyDigest) -> str:
    """Format DailyDigest into standard Markdown for logs, email text, or file export."""
    lines: List[str] = []
    lines.append(f"# 📊 B2B Digest Intelligence — {digest.date}\n")
    lines.append(f"> {digest.executive_summary}\n")
    lines.append(f"**Opportunità rilevate:** {digest.total_items_analyzed}\n")
    lines.append("---\n")

    if not digest.items:
        lines.append("*Nessuna nuova opportunità identificata per oggi.*")
        return "\n".join(lines)

    for idx, item in enumerate(digest.items, 1):
        badge = _get_priority_badge(item.priority)
        category_label = item.category.value.replace("_", " ")

        lines.append(f"## {idx}. {item.title}")
        lines.append(f"- **Categoria:** {category_label} | **Priorità:** {badge}")
        if item.issuer:
            lines.append(f"- **Ente:** {item.issuer}")
        if item.importo_o_agevolazione:
            lines.append(f"- **Importo / Agevolazione:** {item.importo_o_agevolazione}")
        if item.data_scadenza:
            lines.append(f"- **Scadenza:** {item.data_scadenza}")
        lines.append(f"- **Target:** {item.target_audience}")
        lines.append("- **Punti chiave:**")
        for point in item.key_takeaways:
            lines.append(f"  * {point}")
        if item.actionable_step:
            lines.append(f"- **Azione consigliata:** {item.actionable_step}")
        lines.append(f"- [🔗 Consulta fonte ufficiale]({item.original_url})\n")

    lines.append("\n*Elaborato automaticamente da B2B Digest Agent tramite Google Gemini Pro*")
    return "\n".join(lines)


def format_to_email_html(digest: DailyDigest) -> str:
    """Format DailyDigest into styled modern HTML suitable for email clients."""
    items_html = ""
    for idx, item in enumerate(digest.items, 1):
        badge_color = "#dc2626" if item.priority == PriorityLevel.ALTA else ("#d97706" if item.priority == PriorityLevel.MEDIA else "#16a34a")
        points = "".join(f"<li style='margin-bottom: 4px;'>{html.escape(p)}</li>" for p in item.key_takeaways)
        
        items_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <span style="background-color: {badge_color}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{item.priority.value}</span>
                <span style="color: #64748b; font-size: 12px; font-weight: 500;">{html.escape(item.category.value.replace('_', ' '))}</span>
            </div>
            <h3 style="margin: 6px 0 10px 0; color: #0f172a; font-size: 17px; line-height: 1.3;">{idx}. {html.escape(item.title)}</h3>
            <p style="margin: 0 0 6px 0; color: #475569; font-size: 13px;"><strong>🏛 Ente:</strong> {html.escape(item.issuer or 'N/D')} | <strong>💰 Agevolazione/Importo:</strong> {html.escape(item.importo_o_agevolazione or 'N/D')}</p>
            <p style="margin: 0 0 10px 0; color: #475569; font-size: 13px;"><strong>⏰ Scadenza:</strong> {html.escape(item.data_scadenza or 'N/D')} | <strong>🎯 Target:</strong> {html.escape(item.target_audience)}</p>
            <ul style="margin: 0 0 12px 0; padding-left: 20px; color: #334155; font-size: 13px; line-height: 1.5;">
                {points}
            </ul>
            <div style="background-color: #f8fafc; border-left: 3px solid #0284c7; padding: 8px 12px; margin-bottom: 12px; font-size: 13px; color: #0369a1;">
                <strong>⚡ Azione consigliata:</strong> {html.escape(item.actionable_step)}
            </div>
            <a href="{html.escape(item.original_url, quote=True)}" style="display: inline-block; background-color: #0284c7; color: #ffffff; text-decoration: none; padding: 7px 14px; border-radius: 5px; font-size: 13px; font-weight: 600;">Consulta Scheda Ufficiale &rarr;</a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #1e293b;">
        <div style="max-width: 680px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 24px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0 0 6px 0; font-size: 22px; letter-spacing: -0.5px;">📊 B2B Digest Intelligence</h1>
                <p style="margin: 0; color: #94a3b8; font-size: 13px;">Report automatico del {html.escape(digest.date)} &bull; {digest.total_items_analyzed} opportunità analizzate</p>
            </div>
            <div style="background-color: #ffffff; padding: 20px 24px; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #334155; font-style: italic;">{html.escape(digest.executive_summary)}</p>
            </div>
            <div style="padding: 20px 0;">
                {items_html}
            </div>
            <div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 16px 0;">
                Generato da B2B Digest Agent con Google Gemini Pro &bull; GitHub Actions Automation
            </div>
        </div>
    </body>
    </html>
    """
