from datetime import datetime

import psycopg2

from app.db.cases.model import Case
from app.db.database import Session
from app.logger import logger


def insert_case(
    scc_id: str,
    bench_name: str,
    court_name: str,
    case_name: str,
    case_no: str,
    date: datetime,
    advocates: list[str],
    citations: list[str],
    case_text: str,
):
    with Session() as session:
        try:
            existing_case = session.query(Case).filter_by(
                case_name=case_name,
                court_name=court_name,
                date=date,
            ).first()
            if existing_case:
                return existing_case

            case = Case(
                bench_name=bench_name,
                court_name=court_name,
                case_name=case_name,
                case_no=case_no,
                date=date,
                advocates=advocates,
                citations=citations,
                case_text=case_text,
                scc_id=scc_id,
            )

            session.add(case)
            session.commit()

            return case.id

        except Exception as e:
            logger.error({
                "message": "Failed to insert case",
                "error": str(e),
            })
            session.rollback()
