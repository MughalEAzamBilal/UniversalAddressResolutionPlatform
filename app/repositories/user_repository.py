from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User, AccountStatus


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username.strip()).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        clean = identifier.strip().lower()
        return self.db.query(User).filter(
            or_(
                User.username.ilike(clean),
                User.email.ilike(clean)
            )
        ).first()

    def list_users(self, skip: int = 0, limit: int = 50, search: Optional[str] = None) -> List[User]:
        query = self.db.query(User)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.username.ilike(s),
                    User.email.ilike(s),
                    User.full_name.ilike(s)
                )
            )
        return query.order_by(User.id.desc()).offset(skip).limit(limit).all()

    def count_users(self) -> int:
        return self.db.query(User).count()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
