from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.database.base import Base


class AdPlacement:
    TOP_BANNER = "TOP_BANNER"
    BELOW_RESOLVER = "BELOW_RESOLVER"
    SIDEBAR = "SIDEBAR"
    FOOTER = "FOOTER"
    HOME_CONTENT = "HOME_CONTENT"

    ALL = [TOP_BANNER, BELOW_RESOLVER, SIDEBAR, FOOTER, HOME_CONTENT]


class AdType:
    GOOGLE_ADSENSE = "GOOGLE_ADSENSE"
    CUSTOM_HTML = "CUSTOM_HTML"
    BANNER_IMAGE = "BANNER_IMAGE"

    ALL = [GOOGLE_ADSENSE, CUSTOM_HTML, BANNER_IMAGE]


class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    ad_type = Column(String(32), default=AdType.GOOGLE_ADSENSE, nullable=False)
    placement = Column(String(64), default=AdPlacement.BELOW_RESOLVER, index=True, nullable=False)

    # HTML snippet (Google AdSense script, <ins> tag, or custom HTML embed)
    code_snippet = Column(Text, nullable=True)

    # Direct banner image fields
    image_url = Column(String(512), nullable=True)
    target_url = Column(String(512), nullable=True)

    is_active = Column(Boolean, default=True, index=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
