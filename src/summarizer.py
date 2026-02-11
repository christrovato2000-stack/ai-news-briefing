"""
Summarizer module - uses Claude API to analyze, categorize, and summarize
the aggregated news items.
"""
import json
import logging
import os
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

# Categories used for classification
CATEGORIES = [
    "Research Breakthroughs",
    "Product Launches & Updates",
    "Industry News & Business",
    "Policy, Safety & Ethics",
    "Open Source & Developer Tools",
    "Robotics & Autonomous Systems",
    "Other AI & Tech News",
]

CATEGORY_DESCRIPTIONS = {
    "Research Breakthroughs": "New papers, model capabilities, benchmarks, scientific discoveries",
    "Product Launches & Updates": "New AI products, feature releases, version updates",
    "Industry News & Business": "Funding rounds, acquisitions, partnerships, company news",
    "Policy, Safety & Ethics": "Regulations, safety research, alignment, governance",
    "Open Source & Developer Tools": "Open-source releases, APIs, frameworks, developer resources",
    "Robotics & Autonomous Systems": "Robots, autonomous vehicles, physical AI",
    "Other AI & Tech News": "General tech news, miscellaneous",
}


def _build_news_text(items: list[dict], max_items: int = 60) -> str:
    """Format news items into a compact text block for the prompt."""
    lines = []
    for i, item in enumerate(items[:max_items], 1):
        lines.append(
            f"[{i}] SOURCE: {item['source']}\n"
            f"    TITLE: {item['title']}\n"
            f"    URL: {item['url']}\n"
            f"    SUMMARY: {item['summary'][:300]}\n"
        )
    return "\n".join(lines)


def categorize_and_summarize(
    items: list[dict],
    api_key: Optional[str] = None,
    model: str = "claude-opus-4-6",
) -> dict:
    """
    Send news items to Claude and get back:
    - executive_summary: str
    - top_stories: list of {title, url, source, reason}
    - categories: dict of category_name -> list of {title, url, source, summary}

    Returns a structured dict ready for the email template.
    """
    if not items:
        logger.warning("No news items to summarize.")
        return _empty_result()

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=key)
    news_text = _build_news_text(items)
    categories_list = "\n".join(f"- {c}: {CATEGORY_DESCRIPTIONS[c]}" for c in CATEGORIES)

    prompt = f"""You are an expert AI/tech journalist creating a weekly briefing.

Below are {len(items)} news items from the past 7 days across AI and technology.

NEWS ITEMS:
{news_text}

TASK:
Analyze these stories and return a JSON object with EXACTLY this structure:

{{
  "executive_summary": "A 3-5 sentence executive summary of the most important AI and tech developments this week. Be concrete and specific.",
  "top_stories": [
    {{
      "title": "exact title from the list",
      "url": "exact url from the list",
      "source": "exact source from the list",
      "reason": "1-2 sentences explaining why this is a top story"
    }}
  ],
  "categories": {{
    "Research Breakthroughs": [
      {{
        "title": "exact title",
        "url": "exact url",
        "source": "exact source",
        "summary": "2-3 sentence description of what this is about and why it matters"
      }}
    ],
    "Product Launches & Updates": [],
    "Industry News & Business": [],
    "Policy, Safety & Ethics": [],
    "Open Source & Developer Tools": [],
    "Robotics & Autonomous Systems": [],
    "Other AI & Tech News": []
  }}
}}

RULES:
- top_stories: pick the 5 most important/impactful stories across all categories
- Place EVERY story into exactly ONE category; do not omit stories
- Summaries must be original, informative, and specific — avoid vague language
- Return ONLY valid JSON, no markdown fences, no extra text

Categories:
{categories_list}
"""

    logger.info("Calling Claude API (%s) to analyze %d stories…", model, len(items))
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        logger.debug("Claude raw response length: %d chars", len(raw))

        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        _validate_result(result)
        logger.info("Successfully parsed Claude response.")
        return result

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Claude JSON response: %s", exc)
        logger.debug("Raw response: %s", raw[:500])
        return _fallback_result(items)
    except anthropic.APIError as exc:
        logger.error("Claude API error: %s", exc)
        raise


def _validate_result(result: dict) -> None:
    """Basic validation / normalization of the Claude response."""
    if "executive_summary" not in result:
        result["executive_summary"] = "No summary available."
    if "top_stories" not in result or not isinstance(result["top_stories"], list):
        result["top_stories"] = []
    if "categories" not in result or not isinstance(result["categories"], dict):
        result["categories"] = {}
    # Ensure all expected categories exist
    for cat in CATEGORIES:
        if cat not in result["categories"]:
            result["categories"][cat] = []
    # Ensure each story has required fields
    for story in result.get("top_stories", []):
        story.setdefault("title", "Untitled")
        story.setdefault("url", "#")
        story.setdefault("source", "Unknown")
        story.setdefault("reason", "")
    for cat_items in result["categories"].values():
        for story in cat_items:
            story.setdefault("title", "Untitled")
            story.setdefault("url", "#")
            story.setdefault("source", "Unknown")
            story.setdefault("summary", "")


def _empty_result() -> dict:
    return {
        "executive_summary": "No news items were available this week.",
        "top_stories": [],
        "categories": {cat: [] for cat in CATEGORIES},
    }


def _fallback_result(items: list[dict]) -> dict:
    """Best-effort fallback if Claude response can't be parsed."""
    logger.warning("Using fallback result — Claude response could not be parsed.")
    categories = {cat: [] for cat in CATEGORIES}
    categories["Other AI & Tech News"] = [
        {
            "title": item["title"],
            "url": item["url"],
            "source": item["source"],
            "summary": item["summary"],
        }
        for item in items[:40]
    ]
    return {
        "executive_summary": (
            "This week's briefing contains the latest AI and tech news. "
            "Automated summarization encountered an issue; stories are listed below."
        ),
        "top_stories": [
            {
                "title": item["title"],
                "url": item["url"],
                "source": item["source"],
                "reason": item["summary"][:150],
            }
            for item in items[:5]
        ],
        "categories": categories,
    }
