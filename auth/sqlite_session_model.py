from sqlalchemy import Column, String, DateTime, Boolean
from sqlite_db import Base

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    client_id = Column(String, index=True)
    refresh_jti = Column(String, unique=True, index=True)
    refresh_token = Column(String)
    device_info = Column(String)
    issued_at = Column(DateTime)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime)
    revoked = Column(Boolean, default=False)
