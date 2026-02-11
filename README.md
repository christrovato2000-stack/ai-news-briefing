# AI & Tech Weekly Briefing

An automated system that aggregates AI and technology news from multiple sources, uses Claude AI to summarize and categorize stories, and delivers a formatted HTML email every Saturday at 9 AM UTC via GitHub Actions.

---

## What It Does

- **Aggregates** news from 7 sources: Hacker News, ArXiv, TechCrunch, The Verge, MIT Technology Review, VentureBeat, and Wired
- **Analyzes** stories with Claude AI — writes an executive summary, picks top stories, and categorizes everything
- **Delivers** a clean, responsive HTML email with categorized news, descriptions, and links

---

## Project Structure

```
AI News Briefing/
├── .github/
│   └── workflows/
│       └── briefing.yml        # GitHub Actions schedule & pipeline
├── src/
│   ├── aggregator.py           # Fetches news from all sources
│   ├── summarizer.py           # Claude API integration
│   ├── email_sender.py         # Gmail SMTP + HTML rendering
│   └── templates/
│       └── email_template.html # Jinja2 email template
├── main.py                     # Entry point / CLI
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quick Setup (5 steps)

### Step 1 — Fork / push to GitHub

Create a new GitHub repository and push this project to it:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2 — Get a Claude API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in or create an account
3. Navigate to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)

### Step 3 — Set up Gmail App Password

You need a **Gmail App Password** — not your regular Gmail password. App Passwords work even with 2-factor authentication enabled.

1. Go to your [Google Account Security settings](https://myaccount.google.com/security)
2. Ensure **2-Step Verification** is enabled (required for App Passwords)
3. Search for **"App passwords"** or go to: `myaccount.google.com/apppasswords`
4. Click **Create app password**
5. Choose app: **Mail**, device: **Other** → type "AI Briefing"
6. Click **Generate** — copy the 16-character password shown (e.g. `abcd efgh ijkl mnop`)
7. Remove the spaces when you store it: `abcdefghijklmnop`

> **Note:** If you don't see "App passwords," make sure 2-Step Verification is enabled on your account.

### Step 4 — Add GitHub Secrets

In your GitHub repository:

1. Click **Settings** (top navigation)
2. Click **Secrets and variables** → **Actions** (left sidebar)
3. Click **New repository secret** for each of the following:

| Secret Name | Value | Example |
|---|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key | `sk-ant-api03-...` |
| `SENDER_EMAIL` | Gmail address you send FROM | `your.name@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-char App Password (no spaces) | `abcdefghijklmnop` |
| `RECIPIENT_EMAIL` | Email address to receive briefings | `you@example.com` |

> The sender and recipient can be the same Gmail address — the briefing will be sent to yourself.

### Step 5 — Done!

The workflow runs automatically every **Saturday at 9:00 AM UTC**. To test it immediately:

1. Go to **Actions** tab in your repository
2. Click **AI & Tech Weekly Briefing** in the left sidebar
3. Click **Run workflow** → **Run workflow**

---

## Manual / Local Usage

### Install dependencies

```bash
pip install -r requirements.txt
```

### Set environment variables

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
$env:SENDER_EMAIL="you@gmail.com"
$env:GMAIL_APP_PASSWORD="abcdefghijklmnop"
$env:RECIPIENT_EMAIL="you@gmail.com"

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
export SENDER_EMAIL="you@gmail.com"
export GMAIL_APP_PASSWORD="abcdefghijklmnop"
export RECIPIENT_EMAIL="you@gmail.com"
```

### Run the briefing

```bash
# Full run (fetches, summarizes, sends email)
python main.py

# Dry run — no email sent, prints summary to console
python main.py --dry-run

# Save HTML output to file for inspection
python main.py --dry-run --output preview.html

# Look back 14 days instead of 7
python main.py --days 14

# Save the raw JSON briefing for debugging
python main.py --dry-run --save-json briefing.json

# Use a different Claude model
python main.py --model claude-sonnet-4-5-20250929
```

---

## Configuration Options

| CLI Flag | Description | Default |
|---|---|---|
| `--dry-run` | Skip sending email | off |
| `--days N` | Look-back window in days | 7 |
| `--output FILE` | Save rendered HTML to file | none |
| `--save-json FILE` | Save raw briefing JSON | none |
| `--model MODEL` | Claude model to use | `claude-opus-4-6` |

| Env Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `SENDER_EMAIL` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `RECIPIENT_EMAIL` | Destination email address |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

---

## News Sources

| Source | What it covers |
|---|---|
| **Hacker News** | AI/ML posts with >10 points from the past week |
| **ArXiv** | Recent papers from cs.AI, cs.LG (machine learning), cs.CL (NLP) |
| **TechCrunch** | AI-tagged stories from the main feed |
| **The Verge** | AI-related coverage filtered by keyword |
| **MIT Technology Review** | AI and emerging tech stories |
| **VentureBeat** | AI/ML industry news and product coverage |
| **Wired** | Artificial intelligence tag feed |

---

## Email Categories

Claude automatically categorizes every story into one of:

- **Research Breakthroughs** — papers, benchmarks, new capabilities
- **Product Launches & Updates** — releases, features, version updates
- **Industry News & Business** — funding, acquisitions, partnerships
- **Policy, Safety & Ethics** — regulation, alignment, governance
- **Open Source & Developer Tools** — frameworks, APIs, open releases
- **Robotics & Autonomous Systems** — physical AI, robots, autonomous vehicles
- **Other AI & Tech News** — anything else

---

## Troubleshooting

**Email not sending / authentication error**
- Make sure you're using an App Password, not your Gmail login password
- Verify 2-Step Verification is enabled on your Google account
- Check the App Password has no spaces

**"Missing required secrets" error in GitHub Actions**
- Verify all 4 secrets are added under Settings → Secrets and variables → Actions
- Secret names are case-sensitive

**No news items fetched**
- Some RSS feeds may be temporarily unavailable — the pipeline continues with whatever is available
- Run with `LOG_LEVEL=DEBUG` to see detailed feed fetch output

**Claude API errors**
- Check your `ANTHROPIC_API_KEY` is valid and has available credits
- The default model is `claude-opus-4-6`; you can switch to `claude-sonnet-4-5-20250929` if needed

**GitHub Actions not running on schedule**
- GitHub may delay scheduled workflows if your repository is inactive
- Trigger a manual run first to activate the schedule
- Scheduled workflows only run on the default branch

---

## Cost Estimate

A typical weekly run processes ~60–100 news items:
- **Claude API**: approximately $0.05–0.20 per run with `claude-opus-4-6`
- **GitHub Actions**: free tier includes 2,000 minutes/month; each run takes ~2–3 minutes
- **Gmail**: free

---

## License

MIT
