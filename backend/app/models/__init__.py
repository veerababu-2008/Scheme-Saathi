"""SchemeSaathi AI — Model package.

Import all models here so Alembic and the app factory can discover them.
"""

from app.models.activity import (  # noqa: F401
    ChecklistProgress,
    EligibilityCheck,
    RecentlyViewed,
    SavedScheme,
)
from app.models.admin import AdminUser, AuditLog, Feedback  # noqa: F401
from app.models.chat import ChatMessage, ChatSession  # noqa: F401
from app.models.scheme import (  # noqa: F401
    EligibilityRule,
    Scheme,
    SchemeCategory,
    SchemeDocument,
    SchemeSource,
)
from app.models.user import TokenBlocklist, User, UserProfile  # noqa: F401
