from sqlalchemy import Column, Integer, String, Text, Date, ARRAY, UniqueConstraint

from app.db.base import Base


class Case(Base):
    __tablename__ = 'scc_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scc_id = Column(String, unique=True, nullable=False)
    bench_name = Column(Text, nullable=True)
    court_name = Column(Text, nullable=True)
    case_name = Column(Text, nullable=True)
    case_no = Column(Text, nullable=True)
    date = Column(Date, nullable=True)
    advocates = Column(ARRAY(Text), nullable=True)
    citations = Column(ARRAY(Text), nullable=True)
    case_text = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint('case_name', 'court_name', 'date', name='uix_scc_case_court_date'),
    )

    def __repr__(self):
        return f"<Cases(scc_id={self.scc_id}, bench_name={self.bench_name}, court_name={self.court_name}, case_name={self.case_name}, case_no={self.case_no}, date={self.date}, advocates={self.advocates}, citations={self.citations}, case_text={self.case_text})>"
