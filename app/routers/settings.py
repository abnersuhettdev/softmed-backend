from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.settings import Settings, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("/{key}", response_model=Settings)
def get_setting(key: str, db: Session = Depends(get_db)):
    """Get a setting value by key."""
    try:
        settings_service = SettingsService(db)
        setting = settings_service.get_setting_model(key)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found",
            )
        return setting
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}",
        )


@router.put("/{key}", response_model=Settings)
def update_setting(
    key: str,
    setting_update: SettingsUpdate,
    db: Session = Depends(get_db),
):
    """Update a setting value."""
    try:
        settings_service = SettingsService(db)
        setting = settings_service.set_setting(key, setting_update.value, setting_update.updated_by)
        return setting
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}",
        )


@router.get("/", response_model=list[Settings])
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings (admin only - add auth later)."""
    try:
        settings_service = SettingsService(db)
        settings = settings_service.get_all_settings()
        return settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}",
        )

