"""
AI & Tech News Briefing — main entry point.

Usage:
  python main.py                         # run the full pipeline (PDF + email)
  python main.py --dry-run               # fetch + summarize + generate PDF, no email
  python main.py --days 14               # look back 14 days instead of 7
  python main.py --output out.html       # save rendered HTML to file
  python main.py --save-json data.json   # save briefing JSON for debugging
  python main.py --pdf-output brief.pdf  # specify custom PDF output path
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make src importable when running from project root
sys.path.insert(0, str(Path(__file__).parent))

from src.aggregator import aggregate_news
from src.summarizer import categorize_and_summarize
from src.pdf_generator import generate_pdf
from src.email_sender import send_briefing

# ── Logging setup ────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and send an AI & Tech news briefing PDF."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch, summarize, and generate PDF but do not send email.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back when fetching news (default: 7).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save rendered HTML artifact (e.g. briefing_output.html).",
    )
    parser.add_argument(
        "--pdf-output",
        type=str,
        default=None,
        help="Path for the generated PDF (default: AI-Tech-Briefing-YYYY-MM-DD.pdf).",
    )
    parser.add_argument(
        "--save-json",
        type=str,
        default=None,
        help="Path to save the raw briefing JSON (useful for debugging).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-5-20250929",
        help="Claude model to use for summarization (default: claude-sonnet-4-5-20250929).",
    )
    parser.add_argument(
        "--min-stories",
        type=int,
        default=10,
        help="Minimum stories required to proceed (default: 10).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("AI & Tech News Briefing v2.0 starting")
    logger.info("  Look-back: %d days | Dry run: %s | Model: %s",
                args.days, args.dry_run, args.model)
    logger.info("=" * 60)

    # ── Step 1: Aggregate news ────────────────────────────────────────────────
    logger.info("STEP 1/4 — Aggregating news…")
    try:
        news_items = aggregate_news(max_age_days=args.days)
    except Exception as exc:
        logger.error("Fatal error during news aggregation: %s", exc, exc_info=True)
        return 1

    if len(news_items) < args.min_stories:
        logger.error(
            "Only %d stories found (minimum: %d). Aborting. "
            "Check that news sources are reachable.",
            len(news_items), args.min_stories
        )
        return 1

    logger.info("Aggregated %d stories.", len(news_items))

    # ── Step 2: Summarize with Claude ─────────────────────────────────────────
    logger.info("STEP 2/4 — Summarizing with Claude (%s)…", args.model)
    try:
        briefing = categorize_and_summarize(news_items, model=args.model)
    except Exception as exc:
        logger.error("Fatal error during summarization: %s", exc, exc_info=True)
        return 1

    # Optionally save the raw JSON
    if args.save_json:
        try:
            Path(args.save_json).write_text(
                json.dumps(briefing, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("Saved briefing JSON to %s", args.save_json)
        except Exception as exc:
            logger.warning("Could not save JSON: %s", exc)

    total_categorized = sum(len(v) for v in briefing.get("categories", {}).values())
    logger.info(
        "Summarization complete. Top stories: %d | Categorized: %d",
        len(briefing.get("top_stories", [])),
        total_categorized,
    )

    # ── Step 3: Generate PDF ───────────────────────────────────────────────────
    logger.info("STEP 3/4 — Generating premium PDF…")
    try:
        pdf_path = generate_pdf(briefing, output_path=args.pdf_output)
        logger.info("PDF generated: %s", pdf_path)
    except Exception as exc:
        logger.error("Fatal error during PDF generation: %s", exc, exc_info=True)
        return 1

    # ── Step 4: Send email (or dry run) ───────────────────────────────────────
    if args.dry_run:
        logger.info("STEP 4/4 — DRY RUN: skipping email send.")
        print("\n" + "=" * 60)
        print("EXECUTIVE SUMMARY")
        print("=" * 60)
        print(briefing.get("executive_summary", ""))
        print("\nTOP STORIES:")
        for i, s in enumerate(briefing.get("top_stories", []), 1):
            print(f"  {i}. {s.get('title')} [{s.get('source')}]")
        print(f"\nPDF saved to: {pdf_path}")
        print("=" * 60)
    else:
        logger.info("STEP 4/4 — Sending email with PDF attachment…")
        try:
            send_briefing(briefing, pdf_path=str(pdf_path), output_path=args.output)
        except Exception as exc:
            logger.error("Fatal error during email send: %s", exc, exc_info=True)
            return 1

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("Briefing pipeline completed in %.1f seconds.", elapsed)
    logger.info("PDF: %s", pdf_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
