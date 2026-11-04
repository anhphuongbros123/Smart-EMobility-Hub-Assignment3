from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Khởi tạo kết nối CSDL SQLite local
SQLALCHEMY_DATABASE_URL = "sqlite:///./emobility.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các ORM Entities
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()