# 🚀 Job Hunt Agent

A real autonomous agent that generates a **personalised day-by-day job hunt roadmap** for any role and schedules it directly into Google Calendar. Powered by Claude + LangGraph.

---

## What it does

- **Any role, any duration** — AI Engineer, Frontend Dev, Data Scientist, Product Manager, anything
- **Personalised roadmap** — Claude designs phases and daily tasks based on your background
- **Google Calendar integration** — every day scheduled automatically with reminders
- **Workout blocks** — optional morning workouts on days you choose
- **Saturday off** — always skipped
- **Streaming progress** — watch it schedule in real time

---

## Quick Start (Mac)

### Step 1 — Clone / download this project

```bash
cd ~/Desktop
# paste the job-hunt-agent folder here
cd job-hunt-agent
chmod +x run.sh
```

### Step 2 — Get your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Copy it — you'll paste it into the web UI

### Step 3 — Set up Google Calendar API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Calendar API**
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop App**
6. Download the JSON file
7. Save it somewhere, e.g. `~/credentials.json`
8. Note the full path — you'll paste it into the web UI

### Step 4 — Run

```bash
./run.sh
```

Open **http://localhost:8000** in your browser.

On first run, a browser window will open asking you to authorise Google Calendar access. Click Allow. A `token.pickle` file is saved so you only do this once.

---

## Using the Agent

Fill in the form:

| Field | Example |
|---|---|
| Job Role | AI Engineer |
| Total Days | 121 |
| Start Date | Today |
| Background | MS CS, Python basics, QA background. Goal: AI Engineer at OPT-sponsor company |
| Wake Time | 07:00 AM |
| Work Start | 08:00 AM |
| Work Hours | 4 |
| Workout Days | Mon, Tue, Thu, Fri |
| API Key | sk-ant-... |
| Credentials Path | /Users/yourname/credentials.json |

Click **Generate Roadmap + Schedule Calendar** and watch it go.

---

## What gets created in Google Calendar

Each active day (no Saturdays) gets:

- 💪 **Workout event** (on your chosen days) — at Wake Up Time, 1 hour
- 🤖 **AI block event** — 4 hours starting at Work Start Time, containing:
  - 🧠 Learn (1 hr) — specific resource + topic
  - 🔨 Build (1.5 hrs) — specific coding task
  - 🤝 Network (45 min) — LinkedIn/outreach action
  - 🌐 Events (45 min) — community/event to join
  - 30-minute popup reminder

---

## Project Structure

```
job-hunt-agent/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── agent.py         # LangGraph agent + Google Calendar client
│   └── requirements.txt
├── frontend/
│   └── index.html       # Web UI
├── run.sh               # One-click start
└── README.md
```

---

## Customisation

**Change the model**: In `agent.py`, edit `model="claude-sonnet-4-20250514"`

**Change time zone**: In `agent.py`, search for `America/New_York` and replace

**Add more networking resources**: Edit the prompts in `RoadmapGenerator.generate_day_batch()`

---

## Requirements

- Python 3.10+
- Mac (M1/M2/M4 or Intel)
- Anthropic API key
- Google account with Calendar enabled
