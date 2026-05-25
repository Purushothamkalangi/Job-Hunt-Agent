"""
Job Hunt Agent — LangGraph Core
Generates a personalised day-by-day roadmap for any job role
and schedules every event into Google Calendar.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Any, List

import anthropic
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle


SCOPES = ["https://www.googleapis.com/auth/calendar"]

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ── Google Calendar helper ─────────────────────────────────────────────────

class CalendarClient:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        token_path = os.path.join(os.path.dirname(self.credentials_path), "token.pickle")

        if os.path.exists(token_path):
            with open(token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        return build("calendar", "v3", credentials=creds)

    def create_event(self, summary: str, description: str, date: str,
                     start_time: str, end_time: str, color_id: str = "9",
                     reminder_minutes: int = 30):
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": "America/New_York"},
            "end":   {"dateTime": f"{date}T{end_time}:00",   "timeZone": "America/New_York"},
            "colorId": color_id,
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": reminder_minutes}],
            },
        }
        return self.service.events().insert(calendarId="primary", body=event).execute()


# ── Roadmap generator ──────────────────────────────────────────────────────

class RoadmapGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_phases(self, role: str, days: int, background: str) -> list[dict]:
        """Ask Claude to design the phase structure for the roadmap."""
        prompt = f"""You are an expert career coach. Design a structured learning roadmap for someone who wants to become a {role} in {days} days.

Background: {background}

Return ONLY a raw JSON array of phases. No markdown, no backticks.
Schema: [{{"phase": "Phase Name", "start_day": 1, "end_day": 20, "focus": "Brief focus description", "color_id": "9"}}]
Color IDs: 9=blue(learn), 2=green(build), 3=purple(agents/advanced), 5=yellow(apply), 6=orange(interview)
Make phases realistic for {days} days. Last phase should always be "Interview Blitz" (last 15% of days).
Include an "Apply" phase starting at 70% of days.
"""
        resp = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    def generate_day_batch(self, role: str, background: str, phases: list[dict],
                           batch: list[int]) -> list[dict]:
        """Generate tasks for a batch of days."""
        phase_context = "\n".join(
            f"Days {p['start_day']}-{p['end_day']}: {p['phase']} — {p['focus']}"
            for p in phases
        )
        prompt = f"""You are an expert career coach creating a daily job hunt plan for a {role} role.

Background: {background}

Phase structure:
{phase_context}

Generate tasks for EXACTLY these days: {batch}
Return ONLY a raw JSON array. No markdown, no backticks.
Schema: [{{"day": 1, "phase": "Phase Name", "title": "Short action title max 7 words", "learn": "Specific resource + topic (1 hr)", "build": "Specific coding/project task (1.5 hrs)", "network": "Specific LinkedIn/outreach action (45 min)", "events": "Specific community/event to engage (45 min)"}}]
Make every day distinct and progressively harder. Reference real tools, resources, companies relevant to {role}.
For Apply phase: include 5+ job applications daily.
For Interview phase: include LeetCode, system design, behavioral prep.
"""
        resp = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = resp.content[0].text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)


# ── Main agent ─────────────────────────────────────────────────────────────

class JobHuntAgent:
    def __init__(self, anthropic_api_key: str, google_credentials_path: str):
        self.generator = RoadmapGenerator(anthropic_api_key)
        self.calendar = CalendarClient(google_credentials_path)

    def _get_active_dates(self, start_date: str, total_days: int) -> list[dict]:
        """Return list of active dates, skipping Saturdays."""
        result = []
        day_num = 0
        i = 0
        base = datetime.strptime(start_date, "%Y-%m-%d")
        while len(result) < total_days:
            d = base + timedelta(days=i)
            i += 1
            if d.weekday() == 5:  # Saturday = 5
                continue
            day_num += 1
            result.append({
                "date": d.strftime("%Y-%m-%d"),
                "weekday": d.weekday(),   # 0=Mon … 6=Sun
                "weekday_name": DAY_NAMES[d.weekday()],
                "day_num": day_num,
            })
        return result

    def _is_workout_day(self, weekday_name: str, workout_days: List[str]) -> bool:
        return weekday_name in workout_days

    def _get_phase_color(self, phase: str, phases: list[dict]) -> str:
        for p in phases:
            if p["phase"] == phase:
                return p.get("color_id", "9")
        return "9"

    def _format_time(self, time_str: str, add_minutes: int = 0) -> str:
        """Add minutes to a HH:MM string."""
        h, m = map(int, time_str.split(":"))
        total = h * 60 + m + add_minutes
        return f"{total // 60:02d}:{total % 60:02d}"

    async def run(self, req) -> AsyncGenerator[dict, None]:
        total_days = req.days
        start_date = req.start_date
        role = req.role
        background = req.background
        workout_days = req.workout_days
        wake_time = req.wake_time
        work_start = req.work_start
        work_hours = req.work_hours * 60  # convert to minutes

        yield {"type": "log", "message": f"🧠 Designing {total_days}-day roadmap for {role}...", "percent": 2}
        await asyncio.sleep(0)

        # Step 1: Generate phase structure
        try:
            phases = self.generator.generate_phases(role, total_days, background)
            yield {"type": "log", "message": f"✅ {len(phases)} phases designed", "percent": 8}
        except Exception as e:
            yield {"type": "error", "message": f"Phase generation failed: {str(e)}", "percent": 0}
            return

        # Step 2: Get active dates
        active_dates = self._get_active_dates(start_date, total_days)
        yield {"type": "log", "message": f"📅 {len(active_dates)} active days mapped (Saturdays skipped)", "percent": 10}

        # Step 3: Generate roadmap in batches of 10
        all_days = []
        BATCH = 10
        day_numbers = list(range(1, total_days + 1))
        batches = [day_numbers[i:i+BATCH] for i in range(0, len(day_numbers), BATCH)]

        for idx, batch in enumerate(batches):
            pct = 10 + int((idx / len(batches)) * 30)
            yield {"type": "log", "message": f"📝 Generating tasks days {batch[0]}–{batch[-1]}...", "percent": pct}
            try:
                days_data = self.generator.generate_day_batch(role, background, phases, batch)
                all_days.extend(days_data)
            except Exception as e:
                yield {"type": "log", "message": f"⚠️ Batch {idx+1} issue, retrying...", "percent": pct}
                await asyncio.sleep(1)
                try:
                    days_data = self.generator.generate_day_batch(role, background, phases, batch)
                    all_days.extend(days_data)
                except Exception as e2:
                    yield {"type": "error", "message": f"Failed: {str(e2)}", "percent": 0}
                    return
            await asyncio.sleep(0.1)

        yield {"type": "log", "message": f"✅ {len(all_days)} days of tasks ready", "percent": 42}

        # Step 4: Schedule to Google Calendar
        created = 0
        for day_data in all_days:
            day_num = day_data["day"]
            if day_num > len(active_dates):
                break

            active = active_dates[day_num - 1]
            date_str = active["date"]
            wday_name = active["weekday_name"]
            is_workout = self._is_workout_day(wday_name, workout_days)
            color = self._get_phase_color(day_data["phase"], phases)

            pct = 42 + int((created / total_days) * 55)

            try:
                # Workout event
                if is_workout:
                    workout_end = self._format_time(wake_time, 60)
                    self.calendar.create_event(
                        summary=f"💪 Day {day_num}: Morning Workout",
                        description="1-hour workout — strength + cardio. Sets the tone for the day.",
                        date=date_str,
                        start_time=wake_time,
                        end_time=workout_end,
                        color_id="11",
                        reminder_minutes=10,
                    )

                # Calculate AI block times
                learn_start  = work_start
                learn_end    = self._format_time(work_start, 60)
                build_start  = learn_end
                build_end    = self._format_time(build_start, 90)
                net_start    = build_end
                net_end      = self._format_time(net_start, 45)
                event_start  = net_end
                event_end    = self._format_time(event_start, 45)

                desc = (
                    f"📌 Phase: {day_data['phase']}\n\n"
                    f"🧠 LEARN ({learn_start}–{learn_end}):\n{day_data.get('learn','')}\n\n"
                    f"🔨 BUILD ({build_start}–{build_end}):\n{day_data.get('build','')}\n\n"
                    f"🤝 NETWORK ({net_start}–{net_end}):\n{day_data.get('network','')}\n\n"
                    f"🌐 EVENTS ({event_start}–{event_end}):\n{day_data.get('events','')}"
                )

                self.calendar.create_event(
                    summary=f"🤖 Day {day_num} [{day_data['phase']}]: {day_data['title']}",
                    description=desc,
                    date=date_str,
                    start_time=work_start,
                    end_time=event_end,
                    color_id=color,
                    reminder_minutes=30,
                )

                created += 1
                if created % 5 == 0:
                    yield {
                        "type": "progress",
                        "message": f"📅 Scheduled day {day_num} ({wday_name} {date_str})",
                        "percent": pct,
                        "created": created,
                        "total": total_days,
                    }

            except Exception as e:
                yield {"type": "log", "message": f"⚠️ Day {day_num} error: {str(e)[:60]}", "percent": pct}

            await asyncio.sleep(0.05)

        yield {
            "type": "done",
            "message": f"🎯 {created} days scheduled in Google Calendar! Agent complete.",
            "percent": 100,
            "created": created,
            "total": total_days,
            "phases": phases,
        }
