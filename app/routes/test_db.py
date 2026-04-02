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

@router.get("/animals-test")
def animals_test(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT
            a.id,
            a.name AS animal_name,
            s.common_name AS species,
            s.scientific_name,
            a.sex,
            a.status,
            e.name AS enclosure,
            a.date_of_birth,
            a.date_of_arrival
        FROM animals a
        JOIN species s ON a.species_id = s.id
        JOIN enclosures e ON a.enclosure_id = e.id
        ORDER BY a.name
    """))

    rows = result.mappings().all()

    return {
        "total": len(rows),
        "animals": rows
    }
