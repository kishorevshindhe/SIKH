# backend/routes/dashboard_routes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import LibraryFile, User
from auth.dependencies import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    uid = current_user.id
    today = datetime.utcnow().date()

    # Total files + size
    files = db.query(LibraryFile).filter(LibraryFile.owner_id == uid).all()
    total_files = len(files)
    total_size_bytes = sum(f.filesize or 0 for f in files)

    # File type breakdown — FIXED indentation
    type_counts = {}
    for f in files:
        raw = (f.filetype or "other").lower()
        if "pdf" in raw:
            ft = "pdf"
        elif "word" in raw or "docx" in raw:
            ft = "docx"
        elif "text" in raw or "txt" in raw:
            ft = "txt"
        else:
            ft = "other"
        type_counts[ft] = type_counts.get(ft, 0) + 1

    # Recent 5 files
    recent_files = (
        db.query(LibraryFile)
        .filter(LibraryFile.owner_id == uid)
        .order_by(LibraryFile.created_at.desc())
        .limit(5)
        .all()
    )

    # Files uploaded per day (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    weekly = {}
    for f in files:
        if f.created_at and f.created_at >= seven_days_ago:
            day = f.created_at.strftime("%a")
            weekly[day] = weekly.get(day, 0) + 1

    # Total content indexed
    total_chars = sum(len(f.content_text or "") for f in files)

    # Real deltas
    files_today = sum(1 for f in files if f.created_at and f.created_at.date() == today)
    size_today_bytes = sum(f.filesize or 0 for f in files if f.created_at and f.created_at.date() == today)

    # Team members
    all_users = db.query(User).all()
    team = [
        {
            "username": u.username,
            "email": u.email,
            "is_you": u.id == uid,
            "files_count": db.query(LibraryFile).filter(LibraryFile.owner_id == u.id).count()
        }
        for u in all_users
    ]

    # Activity feed — last 10 uploads
    recent_activity = (
        db.query(LibraryFile)
        .order_by(LibraryFile.created_at.desc())
        .limit(10)
        .all()
    )
    activity = []
    for f in recent_activity:
        uploader = db.query(User).filter(User.id == f.owner_id).first()
        time_diff = datetime.utcnow() - f.created_at if f.created_at else None
        if time_diff:
            mins = int(time_diff.total_seconds() // 60)
            if mins < 60:
                time_str = f"{mins} min ago"
            elif mins < 1440:
                time_str = f"{mins // 60} hr ago"
            else:
                time_str = f"{mins // 1440} day ago"
        else:
            time_str = "recently"

        activity.append({
            "username": uploader.username if uploader else "unknown",
            "action": f"uploaded {f.filename}",
            "time": time_str,
            "type": "upload"
        })

    return {
        "total_files": total_files,
        "total_size_bytes": total_size_bytes,
        "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
        "total_content_chars": total_chars,
        "total_terms_indexed": total_chars // 6,
        "file_types": type_counts,
        "weekly_uploads": weekly,
        "files_today": files_today,
        "size_today_kb": round(size_today_bytes / 1024, 1),
        "team": team,
        "activity": activity,
        "recent_files": [
            {
                "file_id": f.id,
                "filename": f.filename,
                "filetype": f.filetype.split("/")[-1].split(".")[-1] if f.filetype else "file",
                "filesize": f.filesize,
                "uploaded_at": str(f.created_at)[:10] if f.created_at else None
            }
            for f in recent_files
        ],
        "percent_indexed": 99 if total_files > 0 else 0
    }