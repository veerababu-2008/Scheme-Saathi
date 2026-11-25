"""SchemeSaathi AI — Chat / Saathi AI models."""

import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title = db.Column(db.String(200), nullable=True)
    language = db.Column(db.String(5), nullable=False, default="en")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref="chat_sessions")
    messages = db.relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan", order_by="ChatMessage.created_at",
    )

    def to_dict(self, include_messages=False):
        data = {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages),
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.String(36), db.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = db.Column(db.String(10), nullable=False)  # user | assistant
    content = db.Column(db.Text, nullable=False)
    citations_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    session = db.relationship("ChatSession", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "citations": self.citations_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
