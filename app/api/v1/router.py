from fastapi import APIRouter

from app.api.v1.certificates import router as certificates_router
from app.api.v1.jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(certificates_router, prefix="/certificates", tags=["Certificates"])
