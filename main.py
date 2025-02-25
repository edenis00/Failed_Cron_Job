import httpx
from pathlib import Path
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware


class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str


class CronPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://staging.telextest.im",
        "http://telextest.im",
        "https://staging.telex.im",
        "https://telex.im"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/integration.json")
def integration_json(request: Request):
    """
    This provides metadata for integrating with Telex.
    """
    base_url = str(request.base_url).rstrip("/")

    integration_json = {
        "data": {
            "date": {"created_at": "2025-02-22", "updated_at": "2025-02-22"},
            "descriptions": {
                "app_name": "Failed Cron Job",
                "app_description": "Monitors failed cron jobs and sends alerts",
                "app_logo": "https://i.imgur.com/lZqvffp.png",
                "app_url": base_url,
                "background_color": "#fff",
            },
            "is_active": False,
            "integration_type": "interval",
            "key_features": [
                "- Monitors failed cron jobs",
                "- Sends alerts to Telex",
                "- Configurable cron monitoring interval"
            ],
            "integration_category": "Monitoring & Logging",
            "author": "Elijah Denis",
            "website": base_url,
            "settings": [
                {
                    "label": "interval",
                    "type": "text",
                    "required": True,
                    "default": "*/5 * * * *"
                },
            ],
            "target_url": f"{base_url}",
            "tick_url": f"{base_url}/tick"
        }
    }

    return integration_json


async def check_cron_failures():
    """
    Checks for failed cron jobs using hardcoded logs.
    """
    failure_logs = [
        "CRON[12345]: (user) CMD (/bin/bash /fail.sh) failed",
        "FAILED TO EXECUTE /USR/SBIN/CRON"
    ]
    return "\n".join(failure_logs) if failure_logs else "No failures detected"


async def send_logs_to_api(failures: str, return_url: str):
    """
    Sends failed cron logs to Telex.
    """
    log_data = {
        "event_name": "Failed Cron Job",
        "username": "Cron Monitor",
        "status": "error",
        "message": f"Failed Cron Jobs Detected:\n{failures}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(return_url, json=log_data)
        print(f"API Response: {response.status_code} - {response.text}")


async def cron_task(payload: CronPayload):
    """
    Fetch cron failures and send them to the return_url.
    """
    failures = await check_cron_failures()

    if failures and failures.strip():
        await send_logs_to_api(failures, payload.return_url)


@app.post("/tick", status_code=202)
def monitor_cron_jobs(payload: CronPayload, background_tasks: BackgroundTasks):
    """Immediately returns 202 and runs cron monitoring in the background."""

    background_tasks.add_task(cron_task, payload)
    return {
        "status": "success",
        "message": "Cron monitoring task has started."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
