"""
Job Hunt Agent - Backend
FastAPI server that runs the LangGraph agent to build
personalized job hunt roadmaps and schedule them to Google Calendar.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio

from agent import JobHuntAgent

app = FastAPI(title="Job Hunt Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")


# ── Request / Response Models ──────────────────────────────────────────────

class HuntRequest(BaseModel):
    role: str                          # e.g. "AI Engineer", "Frontend Developer"
    days: int                          # e.g. 90
    start_date: str                    # e.g. "2026-05-25"
    background: str                    # user's background / skills
    workout_days: list[str]            # e.g. ["Monday","Tuesday","Thursday","Friday"]
    wake_time: str                     # e.g. "07:00"
    work_start: str                    # e.g. "08:00"
    work_hours: int                    # e.g. 4
    anthropic_api_key: str
    google_credentials_path: str       # path to credentials.json

class ProgressEvent(BaseModel):
    type: str     # "log" | "progress" | "done" | "error"
    message: str
    percent: int = 0


# ── Streaming endpoint ─────────────────────────────────────────────────────

@app.post("/api/generate")
async def generate(req: HuntRequest):
    """Stream progress while generating roadmap + scheduling calendar events."""

    async def event_stream():
        agent = JobHuntAgent(
            anthropic_api_key=req.anthropic_api_key,
            google_credentials_path=req.google_credentials_path,
        )
        async for event in agent.run(req):
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
