from datetime import datetime, time, timedelta

from flask import Blueprint, request, session

from app.shared.database import get_db_connection
from app.shared.decorators import login_required


meetings_bp = Blueprint("meetings", __name__, url_prefix="/api/meetings")

MEETING_STATUSES = {"RECRUITING", "CLOSED", "COMPLETED", "CANCELED"}
APPROVAL_TYPES = {"INSTANT", "APPROVAL"}
SKILL_LEVELS = {"BRONZE", "SILVER", "GOLD", "MASTER"}
MEETING_CHAT_ROOM_TYPE = "MEETING"
REQUIRED_FIELDS = (
    "title",
    "description",
    "sport_id",
    "meeting_date",
    "meeting_time",
    "location",
    "max_participants",
    "approval_type",
)


def _close(connection, cursor):
    cursor.close()
    connection.close()


def _meeting_select_sql():
    return """
        SELECT
            m.meeting_id,
            m.title,
            m.description,
            m.sport_id,
            s.sport_name,
            m.host_id,
            u.nickname AS host_name,
            m.meeting_date,
            m.meeting_time,
            m.location,
            m.max_participants,
            m.required_skill_level,
            m.approval_type,
            m.status,
            m.created_at,
            m.updated_at
        FROM meetings AS m
        JOIN sports AS s ON s.sport_id = m.sport_id
        JOIN users AS u ON u.user_id = m.host_id
    """


def _serialize_meeting(meeting):
    if meeting is None:
        return None

    meeting_time = meeting.get("meeting_time")

    if isinstance(meeting_time, timedelta):
        total_minutes = int(meeting_time.total_seconds() // 60)
        hours, minutes = divmod(total_minutes, 60)
        meeting["meeting_time"] = f"{hours:02d}:{minutes:02d}"
    elif isinstance(meeting_time, time):
        meeting["meeting_time"] = meeting_time.strftime("%H:%M")
    elif isinstance(meeting_time, str):
        meeting["meeting_time"] = meeting_time[:5]

    return meeting


def _get_json_body():
    if not request.is_json:
        return None, ({"message": "Content-Type should be JSON."}, 415)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, ({"message": "Format should be dictionary."}, 400)

    return data, None


def _validate_meeting(data, require_status=False):
    required_fields = REQUIRED_FIELDS + (("status",) if require_status else ())
    for field in required_fields:
        if data.get(field) in (None, ""):
            return {"message": f"input {field}."}, 400

    if not isinstance(data["title"], str) or not data["title"].strip():
        return {"message": "title must be non-empty string type."}, 400
    if not isinstance(data["description"], str):
        return {"message": "description must be string type."}, 400
    if not isinstance(data["location"], str) or not data["location"].strip():
        return {"message": "location must be non-empty string type."}, 400

    sport_id = data["sport_id"]
    max_participants = data["max_participants"]
    if isinstance(sport_id, bool) or not isinstance(sport_id, int):
        return {"message": "sport_id must be integer type."}, 400
    if isinstance(max_participants, bool) or not isinstance(max_participants, int):
        return {"message": "max_participants must be integer type."}, 400
    if max_participants < 2:
        return {"message": "max_participants must be at least 2."}, 400

    try:
        datetime.strptime(data["meeting_date"], "%Y-%m-%d")
    except (TypeError, ValueError):
        return {"message": "meeting_date should be YYYY-MM-DD."}, 400

    try:
        datetime.strptime(data["meeting_time"], "%H:%M")
    except (TypeError, ValueError):
        return {"message": "meeting_time should be HH:MM."}, 400

    if data["approval_type"] not in APPROVAL_TYPES:
        return {"message": "approval_type must be INSTANT or APPROVAL."}, 400
    required_skill_level = data.get("required_skill_level")
    if required_skill_level is not None and required_skill_level not in SKILL_LEVELS:
        return {
            "message": (
                "required_skill_level must be null, BRONZE, SILVER, GOLD, or MASTER."
            )
        }, 400
    if require_status and data["status"] not in MEETING_STATUSES:
        return {"message": "Invalid meeting status."}, 400

    return None


@meetings_bp.get("")
def get_meetings():
    keyword = request.args.get("keyword", "").strip()
    sport_id = request.args.get("sport_id", type=int)
    meeting_date = request.args.get("date", "").strip()
    location = request.args.get("location", "").strip()
    status = request.args.get("status", "").strip().upper()

    if meeting_date:
        try:
            datetime.strptime(meeting_date, "%Y-%m-%d")
        except ValueError:
            return {"message": "date should be YYYY-MM-DD."}, 400
    if status and status not in MEETING_STATUSES:
        return {"message": "Invalid meeting status."}, 400

    conditions = []
    params = []
    if keyword:
        conditions.append("(m.title LIKE %s OR m.description LIKE %s)")
        params.extend((f"%{keyword}%", f"%{keyword}%"))
    if sport_id is not None:
        conditions.append("m.sport_id = %s")
        params.append(sport_id)
    if meeting_date:
        conditions.append("m.meeting_date = %s")
        params.append(meeting_date)
    if location:
        conditions.append("m.location LIKE %s")
        params.append(f"%{location}%")
    if status:
        conditions.append("m.status = %s")
        params.append(status)

    sql = _meeting_select_sql()
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY m.meeting_date ASC, m.meeting_time ASC, m.meeting_id ASC"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(params))
        meetings = [_serialize_meeting(meeting) for meeting in cursor.fetchall()]
    finally:
        _close(connection, cursor)

    return {"meetings": meetings, "total": len(meetings)}, 200


@meetings_bp.get("/<int:meeting_id>")
def get_meeting(meeting_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            _meeting_select_sql() + " WHERE m.meeting_id = %s",
            (meeting_id,),
        )
        meeting = _serialize_meeting(cursor.fetchone())
    finally:
        _close(connection, cursor)

    if meeting is None:
        return {"message": "Meeting Not Found"}, 404
    return meeting, 200


@meetings_bp.post("")
@login_required
def create_meeting():
    data, error = _get_json_body()
    if error:
        return error
    error = _validate_meeting(data)
    if error:
        return error

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT sport_id FROM sports WHERE sport_id = %s", (data["sport_id"],))
        if cursor.fetchone() is None:
            return {"message": "Sport Not Found"}, 404

        cursor.execute(
            """
            INSERT INTO meetings (
                host_id, sport_id, title, description, meeting_date, meeting_time,
                location, max_participants, required_skill_level, approval_type,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'RECRUITING')
            """,
            (
                session["user_id"],
                data["sport_id"],
                data["title"].strip(),
                data["description"].strip(),
                data["meeting_date"],
                data["meeting_time"],
                data["location"].strip(),
                data["max_participants"],
                data.get("required_skill_level"),
                data["approval_type"],
            ),
        )
        meeting_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO chat_rooms (room_type, meeting_id)
            VALUES (%s, %s)
            """,
            (MEETING_CHAT_ROOM_TYPE, meeting_id),
        )
        chat_room_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO chat_room_members (chat_room_id, user_id)
            VALUES (%s, %s)
            """,
            (chat_room_id, session["user_id"]),
        )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(connection, cursor)

    return {"message": "Meeting Created", "meeting_id": meeting_id}, 201


def _get_editor(cursor, meeting_id, user_id):
    cursor.execute(
        """
        SELECT m.meeting_id, m.host_id, u.role
        FROM meetings AS m
        JOIN users AS u ON u.user_id = %s
        WHERE m.meeting_id = %s
        """,
        (user_id, meeting_id),
    )
    return cursor.fetchone()


@meetings_bp.put("/<int:meeting_id>")
@login_required
def update_meeting(meeting_id):
    data, error = _get_json_body()
    if error:
        return error
    error = _validate_meeting(data, require_status=True)
    if error:
        return error

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        editor = _get_editor(cursor, meeting_id, session["user_id"])
        if editor is None:
            return {"message": "Meeting Not Found"}, 404
        if editor["host_id"] != session["user_id"] and editor["role"] != "ADMIN":
            return {"message": "Not Authorized"}, 403

        cursor.execute("SELECT sport_id FROM sports WHERE sport_id = %s", (data["sport_id"],))
        if cursor.fetchone() is None:
            return {"message": "Sport Not Found"}, 404

        cursor.execute(
            """
            UPDATE meetings
            SET sport_id = %s,
                title = %s,
                description = %s,
                meeting_date = %s,
                meeting_time = %s,
                location = %s,
                max_participants = %s,
                required_skill_level = %s,
                approval_type = %s,
                status = %s
            WHERE meeting_id = %s
            """,
            (
                data["sport_id"],
                data["title"].strip(),
                data["description"].strip(),
                data["meeting_date"],
                data["meeting_time"],
                data["location"].strip(),
                data["max_participants"],
                data.get("required_skill_level"),
                data["approval_type"],
                data["status"],
                meeting_id,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(connection, cursor)

    return {"message": "Meeting Updated"}, 200


@meetings_bp.delete("/<int:meeting_id>")
@login_required
def delete_meeting(meeting_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        editor = _get_editor(cursor, meeting_id, session["user_id"])
        if editor is None:
            return {"message": "Meeting Not Found"}, 404
        if editor["host_id"] != session["user_id"] and editor["role"] != "ADMIN":
            return {"message": "Not Authorized"}, 403

        cursor.execute("DELETE FROM meetings WHERE meeting_id = %s", (meeting_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _close(connection, cursor)

    return "", 204


@meetings_bp.get("/mine")
@login_required
def get_my_meetings():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            _meeting_select_sql()
            + " WHERE m.host_id = %s"
            + " ORDER BY m.meeting_date ASC, m.meeting_time ASC, m.meeting_id ASC",
            (session["user_id"],),
        )
        meetings = [_serialize_meeting(meeting) for meeting in cursor.fetchall()]
    finally:
        _close(connection, cursor)

    return {"meetings": meetings, "total": len(meetings)}, 200
