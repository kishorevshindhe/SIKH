from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# This creates a local SQLite file called sikh.db
DATABASE_URL = "sqlite:///./sikh.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# This function gives us a database connection when we need it
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()