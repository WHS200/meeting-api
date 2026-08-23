from flask import Blueprint, request, session, jsonify

from app.shared.database import get_db_connection


participation_bp = Blueprint(
    "participation",
    __name__,
    url_prefix="/api/meetings"
)
