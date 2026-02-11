# AI & Tech Weekly Briefing

A fully automated system that generates a **premium PDF report** of the week's most important AI and technology news, then emails it to you every Saturday morning.

**Every Saturday at 9 AM UTC, you receive a beautifully designed PDF in your inbox — zero maintenance required.**

---

## What It Does

1. **Aggregates** 50–80 AI/tech stories from 7 curated sources (Hacker News, ArXiv, TechCrunch, The Verge, MIT Technology Review, VentureBeat, Wired)
2. **Analyzes** all stories using Claude AI — summarizes each, categorizes by topic, identifies the top 5 most significant stories of the week
3. **Generates** a professional multi-page PDF report (McKinsey brief meets Morning Brew aesthetic)
4. **Emails** the PDF to you via Gmail SMTP with a clean HTML summary email

---

## PDF Design

The generated PDF includes:

- **Cover page** — gradient navy/purple background, title, date range, stats (stories/sources/categories)
- **Table of contents** — clean, organized list with page references
- **Executive summary** — AI-written overview in a highlighted callout box + "Week at a Glance" stats
- **Top 5 stories** — numbered badges, extended summaries, color-coded by source, clickable links
- **Category sections** — 2-column card layout, one page per category with gradient header bar
- **Sources & methodology** — all sources listed with URLs and descriptions
- **Running footer** — page numbers, date, "Curated by Claude AI" on every page

Story cards are color-coded by source:

| Source | Color |
|--------|-------|
| Hacker News | Orange |
| ArXiv | Blue |
| TechCrunch | Green |
| The Verge | Purple |
| MIT Tech Review | Red |
| VentureBeat | Amber |
| Wired | Teal |

---

## Prerequisites

- GitHub account (free)
- Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)
- Gmail account with **2-Step Verification** enabled
- Gmail App Password (16 characters — see setup below)

---

## Setup (5–10 minutes)

### Step 1 — Fork or clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-news-briefing.git
cd ai-news-briefing
```

Push to your own GitHub repository if needed.

### Step 2 — Get your Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in or create an account
3. Click **API Keys** in the left sidebar
4. Click **Create Key**, give it a name (e.g., "news-briefing")
5. Copy the key (starts with `sk-ant-...`) — you won't see it again

### Step 3 — Generate a Gmail App Password

> You need 2-Step Verification enabled on your Google account first.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Under "How you sign in to Google", click **2-Step Verification** and enable it if not already on
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Under "Select app", choose **Mail**
5. Under "Select device", choose **Other (custom name)**, type "AI Briefing"
6. Click **Generate**
7. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`) — remove spaces before using it

### Step 4 — Add GitHub Secrets

1. In your GitHub repository, click **Settings** (top navigation bar)
2. In the left sidebar, click **Secrets and variables** → **Actions**
3. Click **New repository secret** for each of these four secrets:

| Secret Name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | Your Claude API key (`sk-ant-...`) |
| `SENDER_EMAIL` | Your Gmail address (`you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Your 16-character app password (no spaces) |
| `RECIPIENT_EMAIL` | Where to send the briefing (can be the same Gmail) |

### Step 5 — Test it manually

1. In your repository, click the **Actions** tab
2. Click **AI & Tech Weekly Briefing** in the left sidebar
3. Click **Run workflow** (top right)
4. Set **Dry run** to `true` for a first test (generates PDF, skips email)
5. Click the green **Run workflow** button
6. Watch the logs — completes in ~2–3 minutes
7. Download the PDF from the **Artifacts** section to verify the output looks great
8. Run again with **Dry run** `false` to test full email delivery

Done! The workflow will now run automatically every Saturday at 9 AM UTC.

---

## Local Development

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run locally (dry run — no email sent)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

python main.py --dry-run
```

The PDF is saved as `AI-Tech-Briefing-YYYY-MM-DD.pdf` in the project root.

### Full local run (sends email)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SENDER_EMAIL="you@gmail.com"
export GMAIL_APP_PASSWORD="yourapppassword"
export RECIPIENT_EMAIL="you@gmail.com"

python main.py
```

### Useful flags

```bash
# Look back 14 days instead of 7
python main.py --dry-run --days 14

# Save JSON data for debugging
python main.py --dry-run --save-json debug.json

# Specify custom PDF path
python main.py --dry-run --pdf-output /tmp/briefing.pdf

# Save HTML artifact
python main.py --dry-run --output briefing.html

# Use a different Claude model (more capable, higher cost)
python main.py --dry-run --model claude-opus-4-6
```

---

## Project Structure

```
├── main.py                      # Entry point — orchestrates all 4 steps
├── requirements.txt             # Python dependencies
├── .github/
│   └── workflows/
│       └── briefing.yml         # GitHub Actions (Saturday 9 AM UTC)
└── src/
    ├── __init__.py
    ├── aggregator.py            # Fetches news from 7 RSS/API sources
    ├── summarizer.py            # Claude API: summarize, categorize, top stories
    ├── pdf_generator.py         # ReportLab PDF generation (premium design)
    ├── email_sender.py          # Gmail SMTP: sends email with PDF attachment
    └── templates/
        └── email_template.html  # Jinja2 HTML template (used for HTML artifact)
```

### Pipeline (4 steps, ~2–3 min total)

```
1. aggregate_news()          ~60 sec   — fetches from 7 sources
2. categorize_and_summarize() ~45 sec  — Claude API call
3. generate_pdf()             ~5 sec   — builds the PDF
4. send_briefing()            ~5 sec   — attaches PDF, sends email
```

---

## Cost Estimate

Claude Sonnet processes ~60 stories:
- Input tokens (~50,000): **~$0.15**
- Output tokens (~8,000): **~$0.06**
- **Per briefing: ~$0.20–0.25**
- **Annual: ~$10–13**

---

## Customization

### Change the schedule

Edit `.github/workflows/briefing.yml`:
```yaml
schedule:
  - cron: "0 9 * * 6"    # 9 AM UTC every Saturday (default)
  # "0 8 * * 1"           # 8 AM UTC every Monday
  # "0 7 * * 1,4"         # 7 AM UTC Monday and Thursday
```

### Add or remove news sources

Edit `src/aggregator.py`. Each source is a function (`fetch_hackernews`, etc.) registered in the `fetchers` list. Add a function returning `list[dict]` with keys `title`, `url`, `summary`, `published`, `source`.

### Change story categories

Edit `CATEGORIES` and `CATEGORY_DESCRIPTIONS` in `src/summarizer.py`. Also update `CATEGORY_ICONS` in `src/pdf_generator.py` and `src/email_sender.py`.

### Customize PDF colors

Edit `src/pdf_generator.py` — update `SOURCE_COLORS`, `CATEGORY_GRADIENTS`, or `TOP_STORY_COLORS` at the top of the file.

---

## Troubleshooting

**"Gmail authentication failed"**
- Must use a **Gmail App Password** (16 chars, no spaces), not your regular password
- Make sure 2-Step Verification is enabled on your Google account
- If you recently changed your Google password, regenerate the app password

**"Only N stories found" / pipeline aborts**
- Some RSS feeds occasionally go down; run `--days 14` to expand the window
- Debug individual sources: `LOG_LEVEL=DEBUG python main.py --dry-run`

**PDF not generated / ReportLab error**
- Ensure `reportlab>=4.2.0` is installed: `pip install "reportlab>=4.2.0"`
- Check that the output directory is writable

**Claude API errors**
- Verify `ANTHROPIC_API_KEY` is correct at [console.anthropic.com](https://console.anthropic.com)
- Check your billing/quota — Sonnet is very affordable for this use case

**GitHub Actions workflow doesn't auto-run**
- GitHub disables scheduled workflows if a repo has no activity for 60 days
- Push a small commit or trigger manually from the Actions tab to re-activate

---

## License

MIT
