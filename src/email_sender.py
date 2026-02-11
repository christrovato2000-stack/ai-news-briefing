"""
Email sender module - renders the Jinja2 HTML template and sends via Gmail SMTP.
"""
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

CATEGORY_ICONS = {
    "Research Breakthroughs": "🔬",
    "Product Launches & Updates": "🚀",
    "Industry News & Business": "💼",
    "Policy, Safety & Ethics": "⚖️",
    "Open Source & Developer Tools": "🛠️",
    "Robotics & Autonomous Systems": "🤖",
    "Other AI & Tech News": "📰",
}


def _render_html(briefing: dict) -> str:
    """Render the email HTML from the Jinja2 template."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("email_template.html")

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    date_range = (
        f"{week_ago.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"
    )

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


def send_briefing(
    briefing: dict,
    recipient_email: Optional[str] = None,
    sender_email: Optional[str] = None,
    gmail_app_password: Optional[str] = None,
    output_path: Optional[str] = None,
) -> None:
    """
    Render the briefing as HTML and send it via Gmail SMTP.

    All parameters fall back to environment variables:
      RECIPIENT_EMAIL, SENDER_EMAIL, GMAIL_APP_PASSWORD
    """
    to_addr = recipient_email or os.environ.get("RECIPIENT_EMAIL")
    from_addr = sender_email or os.environ.get("SENDER_EMAIL")
    password = gmail_app_password or os.environ.get("GMAIL_APP_PASSWORD")

    if not all([to_addr, from_addr, password]):
        missing = [
            name
            for name, val in [
                ("RECIPIENT_EMAIL", to_addr),
                ("SENDER_EMAIL", from_addr),
                ("GMAIL_APP_PASSWORD", password),
            ]
            if not val
        ]
        raise ValueError(f"Missing email configuration: {', '.join(missing)}")

    logger.info("Rendering HTML email template…")
    html_body = _render_html(briefing)

    if output_path:
        try:
            Path(output_path).write_text(html_body, encoding="utf-8")
            logger.info("Saved rendered HTML to %s", output_path)
        except Exception as exc:
            logger.warning("Could not save HTML to %s: %s", output_path, exc)

    now = datetime.now(timezone.utc)
    subject = f"AI & Tech Weekly Briefing – {now.strftime('%B %d, %Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"AI News Briefing <{from_addr}>"
    msg["To"] = to_addr
    msg["X-Mailer"] = "AI-News-Briefing/1.0"

    # Plain-text fallback
    plain_text = _build_plain_text(briefing, now)
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Connecting to Gmail SMTP…")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        logger.info("Email sent successfully to %s", to_addr)
    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "Gmail authentication failed. "
            "Make sure you are using an App Password (not your regular password). "
            "Error: %s",
            exc,
        )
        raise
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending email: %s", exc)
        raise


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
