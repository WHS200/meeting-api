"""Additional features; existing team Blueprints keep their original routes."""
from flask import Blueprint, request, session

features_bp = Blueprint("codex_features", __name__)

from .helpers import APIError
from .friends import friends_bp
from .blocks import blocks_bp
from .direct_chat import direct_chat_bp
from .community import community_bp
from .reports import reports_bp
from .admin import admin_bp, check_active_user
from .helpers import transaction
from .notifications import notifications_bp
from .favorites import favorites_bp
from .profile_stats import profile_stats_bp
from .waitlist import waitlist_bp
from .sports_management import sports_management_bp

features_bp.register_blueprint(friends_bp)
features_bp.register_blueprint(blocks_bp)
features_bp.register_blueprint(direct_chat_bp)
features_bp.register_blueprint(community_bp)
features_bp.register_blueprint(reports_bp)
features_bp.register_blueprint(admin_bp)
features_bp.register_blueprint(notifications_bp)
features_bp.register_blueprint(favorites_bp)
features_bp.register_blueprint(profile_stats_bp)
features_bp.register_blueprint(waitlist_bp)
features_bp.register_blueprint(sports_management_bp)


@features_bp.before_app_request
def enforce_account_status():
    # Covers original HTTP APIs as well as extensions. Logout must remain usable.
    if request.path.startswith("/api/") and session.get("user_id") and request.endpoint not in ("auth.logout", "auth.login"):
        with transaction() as cursor:
            check_active_user(cursor, session["user_id"])


@features_bp.app_errorhandler(APIError)
def feature_error(error):
    return {"message": error.message}, error.status
