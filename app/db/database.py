import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.db.base import Base

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_CONNECTION_STRING")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)