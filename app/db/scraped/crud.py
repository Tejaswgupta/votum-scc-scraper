import psycopg2.errors

from app.db.database import Session
from app.db.scraped.model import Scraped
from app.logger import logger


def insert_scraped_record(
    court_type: str,
    court_name: str,
    year: int,
    month: int,
    day: int,
    completed: bool,
    total_cases: int,
    scraped_cases: int,
):
    with Session() as session:
        try:
            existing_record = (
                session.query(Scraped)
                .filter_by(
                    court_type=court_type,
                    court_name=court_name,
                    year=year,
                    month=month,
                    day=day,
                )
                .first()
            )
            if existing_record:
                return existing_record

            scraped = Scraped(
                court_type=court_type,
                court_name=court_name,
                year=year,
                month=month,
                day=day,
                completed=completed,
                total_cases=total_cases,
                scraped_cases=scraped_cases,
            )

            session.add(scraped)
            session.commit()

            return scraped

        except Exception as e:
            logger.error(
                {
                    "message": "Failed to insert scraped record",
                    "error": str(e),
                }
            )
            session.rollback()
