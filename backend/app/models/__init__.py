"""SchemeSaathi AI — Model package.

Import all models here so Alembic and the app factory can discover them.
"""

from app.models.user import User, UserProfile, TokenBlocklist  # noqa: F401
from app.models.scheme import (                                 # noqa: F401
    Scheme,
    SchemeCategory,
    EligibilityRule,
    SchemeDocument,
    SchemeSource,
)
from app.models.activity import (                               # noqa: F401
    SavedScheme,
    RecentlyViewed,
    EligibilityCheck,
    ChecklistProgress,
)
from app.models.chat import ChatSession, ChatMessage            # noqa: F401
from app.models.admin import AdminUser, AuditLog, Feedback      # noqa: F401
