"""SQLAlchemy 数据库连接与会话。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import get_settings, get_abs_path

_settings = get_settings()
_db_path = get_abs_path(_settings.DB_PATH)
_db_path.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表。在应用启动时调用。"""
    from . import db_models  # noqa: F401  确保模型被注册
    Base.metadata.create_all(bind=engine)
