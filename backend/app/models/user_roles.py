from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 'admin', 'compliance_officer'
    permissions = Column(JSONB, nullable=False, default={})

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<UserRole {self.name}>"