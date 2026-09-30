from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.access_log import AccessLog
from app.models.admin_action import AdminAction
from app.models.login_attempt import LoginAttempt


class LogRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_access(
        self,
        public_id: str,
        address_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None,
        success: bool = True
    ) -> AccessLog:
        log = AccessLog(
            public_id=public_id.lower().strip(),
            address_id=address_id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            referrer=referrer[:500] if referrer else None,
            success=success,
            accessed_at=datetime.now(timezone.utc)
        )
        self.db.add(log)
        self.db.commit()
        return log

    def list_access_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        success: Optional[bool] = None
    ) -> List[AccessLog]:
        query = self.db.query(AccessLog)
        if success is not None:
            query = query.filter(AccessLog.success == success)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                (AccessLog.public_id.ilike(s)) |
                (AccessLog.ip_address.ilike(s))
            )
        return query.order_by(AccessLog.accessed_at.desc()).offset(skip).limit(limit).all()

    def get_resolution_stats(self) -> dict:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(AccessLog).filter(
            AccessLog.accessed_at >= today_start,
            AccessLog.success == True
        ).count()
        failed_count = self.db.query(AccessLog).filter(
            AccessLog.success == False
        ).count()
        total_count = self.db.query(AccessLog).count()
        return {
            "today_resolutions": today_count,
            "failed_resolutions": failed_count,
            "total_resolutions": total_count,
        }

    def log_admin_action(
        self,
        admin_user_id: Optional[int],
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[str] = None
    ) -> AdminAction:
        item = AdminAction(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(item)
        self.db.commit()
        return item

    def list_admin_actions(self, skip: int = 0, limit: int = 50) -> List[AdminAction]:
        return self.db.query(AdminAction).order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()

    def list_login_attempts(self, skip: int = 0, limit: int = 50) -> List[LoginAttempt]:
        return self.db.query(LoginAttempt).order_by(LoginAttempt.attempted_at.desc()).offset(skip).limit(limit).all()
