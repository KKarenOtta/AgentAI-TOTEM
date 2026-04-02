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

@router.get("/animals")
def list_animals(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT a.name, s.common_name
        FROM animals a
        JOIN species s ON a.species_id = s.id
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})

    return {"animals": result.mappings().all()}
