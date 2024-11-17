from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint

from app.db.base import Base


class Scraped(Base):
    __tablename__ = 'scc_cases_scraped'

    id = Column(Integer, primary_key=True)
    court_type = Column(String(255), nullable=False)
    court_name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    completed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('court_type', 'court_name', 'year', 'month', 'day', name='_court_name_year_month_day_uc'),
    )

    def __repr__(self):
        return f"<Scraped(id={self.id}, court_type={self.court_type}, court_name={self.court_name}, " \
               f"year={self.year}, month={self.month}, day={self.day}, completed={self.completed})>"
