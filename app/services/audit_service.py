from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.log_repository import LogRepository
from app.models.admin_action import AdminAction
from app.core.logging import logger


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.log_repo = LogRepository(db)

    def log_action(
        self,
        admin_user_id: Optional[int],
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> AdminAction:
        item = self.log_repo.log_admin_action(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details
        )
        logger.info(f"Admin Action: {action} on {target_type}:{target_id} by admin_id={admin_user_id}")
        return item
