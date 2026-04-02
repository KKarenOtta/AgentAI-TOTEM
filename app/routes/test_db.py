from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from DB.session import get_db

router = APIRouter()

@router.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT DATABASE() AS banco_atual"))
    row = result.mappings().first()
    return row
