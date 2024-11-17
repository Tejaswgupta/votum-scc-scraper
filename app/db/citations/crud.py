import psycopg2

from app.db.citations.model import Citation
from app.db.database import Session
from app.logger import logger


def insert_citation(
    unique_id: str,
    case_id: int,
    title: str,
    text: str,
    type: str,
):
    with Session() as session:
        try:
            exsting_citation = session.query(Citation).filter_by(unique_id=unique_id).first()
            if exsting_citation:
                return exsting_citation

            citation = Citation(
                unique_id=unique_id,
                case_id=case_id,
                title=title,
                text=text,
                type=type,
            )

            session.add(citation)
            session.commit()

            return citation

        except Exception as e:
            logger.error({
                "message": "Failed to insert citation",
                "error": str(e),
            })
            session.rollback()
