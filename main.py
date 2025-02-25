import re
import json
import httpx
import os
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

TEST_LOG_PATH = os.path.abspath("/tmp/test_syslog.log")
print(f"Test log path: {TEST_LOG_PATH}")

log_paths = [
    "/var/log/syslog",
    "/var/log/cron.log",
    "/var/log/messages",
    "/var/log/auth.log",
    TEST_LOG_PATH
]    


@app.get("/integration.json")
def integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")

    # Find the first existing log path dynamically
    cron_log_path = next((path for path in log_paths if Path(path).exists()), TEST_LOG_PATH)

    integration_json = {
        "data": {
            "date": {"created_at": "2025-02-22", "updated_at": "2025-02-22"},
            "descriptions": {
                "app_name": "Failed Cron Job",
                "app_description": "Monitors failed cron job and sends alerts",
                "app_logo": "https://i.imgur.com/lZqvffp.png",
                "app_url": base_url,
                "background_color": "#fff",
            },
            "is_active": False,
            "integration_type": "interval",
            "key_features": [
                "- Monitors failed cron jobs",
                "- Sends alerts to telex",
                " Configurable cron log path and monitoring interval"
            ],
            "integration_category": "Monitoring & Logging",
            "author": "Elijah Denis",
            "website": base_url,
            "settings": [
                {
                    "label": "cron_log_path",
                    "type": "dropdown",
                    "required": True,
                    "default": cron_log_path,
                    "options": log_paths
                },
                {
                    "label": "interval_integrations",
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


async def check_cron_failures(log_path: str):
    """
    Checks for failed logs in the cron log file
    Returns a string containing the failed logs
    """
    error_messages = []
    log_file = Path(log_path)

    if not log_file.exists():
        return "Log file does not exist or is inaccessible."

    try:
        with log_file.open("r", encoding="utf-8") as file:
            log_lines = file.readlines()
            print(log_lines)

            failure_patterns = [
                r"CRON\[[0-9]+\]: \(.*\) CMD \(.*\) failed",
                r"CRON\[[0-9]+\]: (.*error.*|.*failed.*)",
                r"pam_unix\(cron:session\): session closed for user .*",
                r"FAILED TO EXECUTE /USR/SBIN/CRON",
                r"CRON\[[0-9]+\]: error.*",
                r"CMD \((.*)\) FAILED",
            ]

            for line in log_lines[-100:]:
                for pattern in failure_patterns:
                    if re.search(pattern, line):
                        error_messages.append(line.strip())

    except Exception as e:
        return f"Error reading log file: {str(e)}"

    return "\n".join(error_messages) if error_messages else None


async def cron_task(payload: CronPayload):
    """
    Task for cron jobs and failures and send results.
    """

    cron_log_path = next((path for path in log_paths if Path(path).exists()), TEST_LOG_PATH)

    for setting in payload.settings:
        if setting.label == "cron_log_path" and Path(setting.default).exists():
            cron_log_path = setting.default

    failures = await check_cron_failures(cron_log_path)

    if failures is not None and failures.strip():
        telex_format = {
            "event_name": "Failed Cron Job",
            "username": "Cron Monitor",
            "status": "error",
            "message": f"Failed Cron Jobs Detected:\n{failures}"
        }

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                payload.return_url,
                json=telex_format,
                headers=headers
            )
        print(f"Telex Response: {response.status_code} - {response.text}")


@app.post("/tick", status_code=202)
def monitor_cron_jobs(payload: CronPayload, background_tasks: BackgroundTasks):
    """Immediately returns 202 and runs cron monitoring in the background."""

    background_tasks.add_task(cron_task, payload)
    print(
        "Telex received Data: ",
        json.dumps(payload.dict(), indent=2)
    )
    return {
        "status": "success",
        "message": "Cron monitoring task has been completed."
    }

@app.get("/check-log")
def check_log_file():
    log_path = "/opt/render/project/src/test/logs/test_syslog.log"
    log_file = Path(log_path)

    if not log_file.exists():
        return {"error": "Log file does not exist", "path": log_path}

    try:
        with log_file.open("r", encoding="utf-8") as file:
            sample_logs = file.readlines()[:5]  # Read first 5 lines
        return {"status": "File exists", "sample_logs": sample_logs}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
