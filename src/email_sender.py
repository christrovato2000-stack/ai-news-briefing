"""
Email sender module - renders the Jinja2 HTML template and sends via Gmail SMTP
with the premium PDF briefing attached.
"""
import logging
import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

CATEGORY_ICONS = {
    "Research Breakthroughs":        "🔬",
    "Product Launches & Updates":    "🚀",
    "Industry News & Business":      "💼",
    "Policy, Safety & Ethics":       "⚖️",
    "Open Source & Developer Tools": "🛠️",
    "Robotics & Autonomous Systems": "🤖",
    "Other AI & Tech News":          "📰",
}


def _render_html(briefing: dict) -> str:
    """Render the email HTML from the Jinja2 template."""
    project_root = Path(__file__).resolve().parent.parent
    template_dir = project_root / "src" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("email_template.html")

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    date_range = f"{week_ago.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"

    categories = briefing.get("categories", {})
    all_stories = [s for cat_stories in categories.values() for s in cat_stories]
    sources = {s.get("source", "Unknown") for s in all_stories}
    non_empty_cats = [c for c, stories in categories.items() if stories]

    context = {
        "date_range": date_range,
        "total_stories": len(all_stories),
        "source_count": len(sources),
        "category_count": len(non_empty_cats),
        "top_story_count": len(briefing.get("top_stories", [])),
        "executive_summary": briefing.get("executive_summary", ""),
        "top_stories": briefing.get("top_stories", []),
        "categories": categories,
        "category_icons": CATEGORY_ICONS,
        "generated_at": now.strftime("%A, %B %d, %Y at %H:%M UTC"),
    }
    return template.render(**context)


def _build_plain_text(briefing: dict, now: datetime) -> str:
    """Generate a plain-text fallback version of the briefing."""
    lines = [
        "AI & TECH WEEKLY BRIEFING",
        f"Generated: {now.strftime('%B %d, %Y')}",
        "=" * 60,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        briefing.get("executive_summary", ""),
        "",
        "TOP STORIES",
        "-" * 40,
    ]
    for i, story in enumerate(briefing.get("top_stories", []), 1):
        lines.append(f"{i}. {story.get('title', '')} [{story.get('source', '')}]")
        lines.append(f"   {story.get('url', '')}")
        lines.append(f"   {story.get('reason', '')}")
        lines.append("")

    for category, stories in briefing.get("categories", {}).items():
        if not stories:
            continue
        lines += ["", category.upper(), "-" * 40]
        for story in stories:
            lines.append(f"• {story.get('title', '')} [{story.get('source', '')}]")
            lines.append(f"  {story.get('url', '')}")
            lines.append(f"  {story.get('summary', '')}")
            lines.append("")

    return "\n".join(lines)


def _build_email_html(briefing: dict, date_range: str, pdf_filename: str) -> str:
    """Build a simple, clean email body HTML for the PDF delivery email."""
    categories = briefing.get("categories", {})
    all_stories = [s for cat in categories.values() for s in cat]
    sources = {s.get("source", "Unknown") for s in all_stories}
    non_empty_cats = [c for c, stories in categories.items() if stories]
    total = len(all_stories)
    source_count = len(sources)
    cat_count = len(non_empty_cats)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI & Tech Weekly Briefing</title>
</head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:32px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0D1B2A,#1B0D2A);border-radius:12px 12px 0 0;padding:32px 36px;text-align:center;">
            <div style="font-size:13px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">Weekly Briefing</div>
            <div style="font-size:28px;font-weight:800;color:#FFFFFF;margin-bottom:6px;">AI &amp; Tech</div>
            <div style="font-size:14px;color:#CBD5E1;">{date_range}</div>
          </td>
        </tr>

        <!-- Stats bar -->
        <tr>
          <td style="background:#1E293B;padding:16px 36px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="text-align:center;border-right:1px solid #334155;">
                  <div style="font-size:24px;font-weight:800;color:#F59E0B;">{total}</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Stories</div>
                </td>
                <td style="text-align:center;border-right:1px solid #334155;">
                  <div style="font-size:24px;font-weight:800;color:#F59E0B;">{source_count}</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Sources</div>
                </td>
                <td style="text-align:center;">
                  <div style="font-size:24px;font-weight:800;color:#F59E0B;">{cat_count}</div>
                  <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Categories</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#FFFFFF;padding:32px 36px;">
            <p style="margin:0 0 16px;font-size:16px;font-weight:600;color:#111827;">
              Your weekly briefing is attached. 📎
            </p>
            <p style="margin:0 0 20px;font-size:14px;color:#4B5563;line-height:1.7;">
              This week's <strong>AI &amp; Tech Weekly Briefing</strong> covers {date_range} with
              <strong>{total} stories</strong> from <strong>{source_count} sources</strong>
              across <strong>{cat_count} categories</strong>.
            </p>

            <!-- PDF callout box -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#EEF2FF;border-radius:8px;border:1px solid #C7D2FE;margin-bottom:24px;">
              <tr>
                <td style="padding:16px 20px;">
                  <div style="font-size:13px;font-weight:700;color:#3730A3;margin-bottom:4px;">📄 {pdf_filename}</div>
                  <div style="font-size:12px;color:#6366F1;">Open the attached PDF for your full curated weekly briefing with clickable links.</div>
                </td>
              </tr>
            </table>

            <p style="margin:0;font-size:13px;color:#9CA3AF;">
              This is an automated briefing. Curated by Claude AI, delivered via GitHub Actions.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F9FAFB;border-radius:0 0 12px 12px;padding:16px 36px;border-top:1px solid #E5E7EB;">
            <p style="margin:0;font-size:11px;color:#9CA3AF;text-align:center;">
              AI &amp; Tech Weekly Briefing &nbsp;•&nbsp; Curated by Claude AI &nbsp;•&nbsp; Powered by GitHub Actions
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_briefing(
    briefing: dict,
    pdf_path: Optional[str] = None,
    recipient_email: Optional[str] = None,
    sender_email: Optional[str] = None,
    gmail_app_password: Optional[str] = None,
    output_path: Optional[str] = None,
    max_retries: int = 3,
) -> None:
    """
    Render the briefing and send it via Gmail SMTP with PDF attached.

    Args:
        briefing: Structured briefing dict from summarizer
        pdf_path: Path to the generated PDF file to attach
        recipient_email: Override recipient (falls back to RECIPIENT_EMAIL env var)
        sender_email: Override sender (falls back to SENDER_EMAIL env var)
        gmail_app_password: Override password (falls back to GMAIL_APP_PASSWORD env var)
        output_path: If set, also save the rendered HTML to this path
        max_retries: Number of SMTP send attempts with exponential backoff
    """
    to_addr  = recipient_email    or os.environ.get("RECIPIENT_EMAIL")
    from_addr = sender_email      or os.environ.get("SENDER_EMAIL")
    password  = gmail_app_password or os.environ.get("GMAIL_APP_PASSWORD")

    if not all([to_addr, from_addr, password]):
        missing = [
            name for name, val in [
                ("RECIPIENT_EMAIL",    to_addr),
                ("SENDER_EMAIL",       from_addr),
                ("GMAIL_APP_PASSWORD", password),
            ] if not val
        ]
        raise ValueError(f"Missing email configuration: {', '.join(missing)}")

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    date_range = f"{week_ago.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"

    # Validate PDF before building the message
    pdf_file = Path(pdf_path) if pdf_path else None
    if pdf_file and not pdf_file.exists():
        logger.warning("PDF file not found at %s — sending without attachment", pdf_file)
        pdf_file = None

    pdf_filename = pdf_file.name if pdf_file else f"AI-Tech-Briefing-{now.strftime('%Y-%m-%d')}.pdf"

    # Build subject
    subject = f"AI & Tech Weekly Briefing — {date_range}"

    # Build message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = f"AI News Briefing <{from_addr}>"
    msg["To"]      = to_addr
    msg["X-Mailer"] = "AI-News-Briefing/2.0"

    # Multipart/alternative for plain + HTML body
    body_part = MIMEMultipart("alternative")

    plain_text = _build_plain_text(briefing, now)
    body_part.attach(MIMEText(plain_text, "plain", "utf-8"))

    html_body = _build_email_html(briefing, date_range, pdf_filename)
    body_part.attach(MIMEText(html_body, "html", "utf-8"))

    msg.attach(body_part)

    # Optionally save HTML for debugging
    if output_path:
        try:
            # Also render the full Jinja2 template for the HTML artifact
            full_html = _render_html(briefing)
            Path(output_path).write_text(full_html, encoding="utf-8")
            logger.info("Saved rendered HTML to %s", output_path)
        except Exception as exc:
            logger.warning("Could not save HTML: %s", exc)

    # Attach PDF
    if pdf_file:
        logger.info("Attaching PDF: %s (%.1f KB)", pdf_filename,
                    pdf_file.stat().st_size / 1024)
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()
        pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition", "attachment", filename=pdf_filename
        )
        msg.attach(pdf_attachment)
    else:
        logger.warning("No PDF attached — sending email body only.")

    # Send with retry logic
    logger.info("Sending email to %s…", to_addr)
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(from_addr, password)
                server.sendmail(from_addr, to_addr, msg.as_string())
            logger.info("Email sent successfully to %s (attempt %d)", to_addr, attempt)
            return
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(
                "Gmail authentication failed. "
                "Use an App Password (16 chars), NOT your regular Gmail password. "
                "Error: %s", exc
            )
            raise  # Auth errors won't be fixed by retrying
        except smtplib.SMTPException as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("SMTP error (attempt %d/%d): %s — retrying in %ds",
                               attempt, max_retries, exc, wait)
                time.sleep(wait)
            else:
                logger.error("SMTP error after %d attempts: %s", max_retries, exc)

    if last_exc:
        raise last_exc
