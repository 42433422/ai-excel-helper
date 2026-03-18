from contextlib import contextmanager
from app.db import SessionLocal


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_dependency():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
