from sqlalchemy import Column, Integer, String, Boolean
from app.database.base import Base


class IdGenerationPattern(Base):
    __tablename__ = "id_generation_patterns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    pattern = Column(String(32), nullable=False)
    priority = Column(Integer, unique=True, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)
