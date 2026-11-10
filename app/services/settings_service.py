from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.settings import Settings


class SettingsService:
    def __init__(self, db: Session):
        """Initialize SettingsService with a database session."""
        self.db = db

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key."""
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        return setting.value if setting else None

    def get_setting_model(self, key: str) -> Optional[Settings]:
        """Get a setting model by key."""
        return self.db.query(Settings).filter(Settings.key == key).first()

    def set_setting(self, key: str, value: str, updated_by: Optional[int] = None) -> Settings:
        """Set or update a setting value."""
        setting = self.db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            if updated_by:
                setting.updated_by = updated_by
        else:
            setting = Settings(key=key, value=value, updated_by=updated_by)
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def get_all_settings(self) -> List[Settings]:
        """Get all settings."""
        return self.db.query(Settings).all()

    def is_telemedicine_enabled(self) -> bool:
        """Check if telemedicine is globally enabled."""
        value = self.get_setting("telemedicine_enabled")
        return value and value.lower() == "true"

