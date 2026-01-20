from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

@router.get("", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    try:
        return db.query(models.APR).order_by(models.APR.id.desc()).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))
