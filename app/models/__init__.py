"""
PROXVEL Backend - Models init.
Importar todos los modelos para que Base.metadata los registre.
"""

from app.models.base import Base
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.destination_media_model import DestinationMedia
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking
from app.models.user_model import User
from app.models.traveler_profile_model import TravelerProfile
from app.models.favorite_model import Favorite
from app.models.review_model import Review
from app.models.review_aspect_rating_model import ReviewAspectRating
from app.models.monthly_review_batch_model import MonthlyReviewBatch
from app.models.model_update_run_model import ModelUpdateRun
from app.models.visit_model import Visit
from app.models.announcement_model import Announcement
from app.models.engine_config_model import EngineConfig
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.archive_model import Archive
from app.models.app_release_model import AppRelease
from app.models.notification_model import Notification, AnnouncementRead, NotificationPreference
from app.models.password_reset_model import PasswordResetCode

__all__ = [
    "Base",
    "Destination",
    "TourismCatalog",
    "DestinationAspectScore",
    "ClimateScore",
    "CrowdScore",
    "ContextualRanking",
    "User",
    "TravelerProfile",
    "Favorite",
    "Review",
    "ReviewAspectRating",
    "MonthlyReviewBatch",
    "ModelUpdateRun",
    "Visit",
    "Announcement",
    "EngineConfig",
    "DestinationTag",
    "DestinationMonthContext",
    "Archive",
    "AppRelease",
    "Notification",
    "AnnouncementRead",
    "NotificationPreference",
    "PasswordResetCode",
]
from app.models.review_report_model import ReviewReport
from app.models.audit_event_model import AuditEvent
