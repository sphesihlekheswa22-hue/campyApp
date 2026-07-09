import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models import BackgroundJob, JobStatus


def enqueue_job(db: Session, job_type: str, payload: dict, max_attempts: int = 3) -> BackgroundJob:
    job = BackgroundJob(
        job_type=job_type,
        payload_json=json.dumps(payload),
        status=JobStatus.pending,
        max_attempts=max_attempts,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_pending_jobs(limit: int = 5) -> int:
    """Process queued jobs — called from app lifespan worker."""
    db = SessionLocal()
    processed = 0
    try:
        jobs = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.status == JobStatus.pending)
            .order_by(BackgroundJob.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        for job in jobs:
            job.status = JobStatus.running
            job.attempts += 1
            job.started_at = datetime.now(timezone.utc)
            db.commit()
            try:
                _run_job(job)
                job.status = JobStatus.complete
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = None
            except Exception as e:
                print(f"[JOB ERROR] {job.job_type} #{job.id}: {e}")
                job.error_message = str(e)[:500]
                if job.attempts >= job.max_attempts:
                    job.status = JobStatus.failed
                else:
                    job.status = JobStatus.pending
                job.completed_at = datetime.now(timezone.utc)
            db.commit()
            processed += 1
    finally:
        db.close()
    return processed


def _run_job(job: BackgroundJob) -> None:
    payload = json.loads(job.payload_json or "{}")
    if job.job_type == "extraction":
        from app.extraction.pipeline import run_extraction
        run_extraction(
            int(payload["report_id"]),
            payload.get("report_year"),
        )
    elif job.job_type == "scheduled_report":
        from app.services.scheduled_report_service import send_scheduled_report
        send_scheduled_report(int(payload["schedule_id"]))
    elif job.job_type == "health_check":
        from app.services.alert_service import run_health_alerts
        run_health_alerts()
    else:
        raise ValueError(f"Unknown job type: {job.job_type}")
