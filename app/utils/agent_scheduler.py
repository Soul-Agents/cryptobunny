from datetime import datetime, timezone
from app.utils.db import get_db

def create_default_schedule(client_id: str) -> dict:
    """
    Create a default schedule for an agent that doesn't have one.
    Default schedule runs once per day during business hours.
    For agents with project cap > 100, runs 3 times per day.
    """
    now = datetime.now(timezone.utc)
    
    # Get rate limits to determine runs_per_day
    db = get_db()
    rate_limits = db.rate_limits.find_one({"client_id": client_id})
    project_cap = rate_limits.get("rate_limits", {}).get("project_cap", 100) if rate_limits else 100
    
    # Set runs_per_day based on project cap
    runs_per_day = 3 if project_cap > 100 else 1
    
    default_schedule = {
        "client_id": client_id,
        "start_time": "09:00",  # 9 AM UTC
        "end_time": "17:00",    # 5 PM UTC
        "runs_per_day": runs_per_day,
        "last_run_date": now.strftime("%Y-%m-%d"),
        "last_run_times": []
    }
    
    db.agent_schedules.update_one(
        {"client_id": client_id},
        {"$set": default_schedule},
        upsert=True
    )
    
    return default_schedule

def should_run_agent_now(schedule):
    db = get_db()
    now = datetime.now(timezone.utc)
    now_time = now.time()
    start = datetime.strptime(schedule["start_time"], "%H:%M").time()
    end = datetime.strptime(schedule["end_time"], "%H:%M").time()
    print('DATEEEEE',start, end, now_time)
    print("schedule",schedule)
    if not (start <= now_time <= end):
        return False

    # Get rate limits for the client
    rate_limits = db.rate_limits.find_one({"client_id": schedule["client_id"]})
    project_cap = rate_limits.get("project_cap", 100) if rate_limits else 100
    print("project_cap",project_cap)

    # Adjust runs_per_day based on project cap
    runs_per_day = 3 if project_cap > 100 else 1
    print("runs_per_day",runs_per_day)

    # Check if we need to reset run times for a new day
    last_run_date = schedule.get("last_run_date", None)
    today_str = now.strftime("%Y-%m-%d")
    if last_run_date != today_str:
        db.agent_schedules.update_one(
            {"client_id": schedule["client_id"]},
            {
                "$set": {
                    "last_run_times": [],
                    "last_run_date": today_str
                }
            }
        )
        run_times = []
    else:
        run_times = schedule.get("last_run_times", [])

    print("run_times",run_times)
    if len(run_times) >= runs_per_day:
        return False

    if run_times:
        last_run_time = datetime.strptime(run_times[-1], "%H:%M").time()
        last_run_dt = datetime.combine(now.date(), last_run_time).replace(tzinfo=timezone.utc)
        minutes_since = (now - last_run_dt).total_seconds() / 60
        if minutes_since < 1:
            return False

    run_times.append(now_time.strftime("%H:%M"))
    db.agent_schedules.update_one(
        {"client_id": schedule["client_id"]},
        {"$set": {"last_run_times": run_times, "last_run_date": today_str}}
    )

    return True