from pydantic import BaseModel


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str
