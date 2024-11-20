from datetime import date

from app.db.database import Session
from app.db.scraped.model import Scraped


def get_scraping_status(date: date = None) -> dict:
    """Get status of scraping for a specific date or all dates"""
    with Session() as session:
        query = session.query(Scraped)
        if date:
            query = query.filter(
                Scraped.year == date.year,
                Scraped.month == date.month,
                Scraped.day == date.day,
            )

        records = query.all()

        status = {
            "total_days": len(records),
            "completed_days": len([r for r in records if r.completed]),
            "total_cases": sum(r.total_cases or 0 for r in records),
            "scraped_cases": sum(r.scraped_cases for r in records),
            "error_count": sum(r.error_count for r in records),
            "in_progress": len(
                [r for r in records if r.scraped_cases > 0 and not r.completed]
            ),
        }

        return status
