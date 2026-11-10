from fastapi import APIRouter

from app.schemas.reports import ReportResponse

router = APIRouter()


@router.get("/", response_model=ReportResponse)
def get_reports():
    return {"message": "This is the reports router."}
