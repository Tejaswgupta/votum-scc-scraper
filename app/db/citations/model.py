from sqlalchemy import Column, Integer, Text, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Citation(Base):
    __tablename__ = 'scc_cases_citations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_id = Column(String, unique=True)
    case_id = Column(Integer, ForeignKey('scc_cases.id'))
    title = Column(Text)
    text = Column(Text)
    type = Column(Text)

    def __repr__(self):
        return f"<Citation(unique_id={self.unique_id}, title={self.title}, text={self.text}, type={self.type})>"
