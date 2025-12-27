from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from ..database import Base
import json


class StackConfig(Base):
    """Stores the user's stack configuration (enabled services, profile, etc.)"""
    __tablename__ = "stack_config"

    id = Column(Integer, primary_key=True, index=True)
    profile = Column(String(20), nullable=False, default="cpu")
    environment = Column(String(20), nullable=False, default="private")
    enabled_services_json = Column(Text, nullable=False, default="[]")
    port_overrides_json = Column(Text, nullable=False, default="{}")
    setup_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def enabled_services(self) -> list:
        """Get enabled services as a list."""
        try:
            return json.loads(self.enabled_services_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @enabled_services.setter
    def enabled_services(self, value: list):
        """Set enabled services from a list."""
        self.enabled_services_json = json.dumps(value)

    @property
    def port_overrides(self) -> dict:
        """Get port overrides as a dict."""
        try:
            return json.loads(self.port_overrides_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @port_overrides.setter
    def port_overrides(self, value: dict):
        """Set port overrides from a dict."""
        self.port_overrides_json = json.dumps(value)
