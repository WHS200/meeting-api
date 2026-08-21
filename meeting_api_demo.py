from datetime import datetime
import sqlite3

from flask import Flask, g, jsonify, request, session


def create_app(database=":memory:"):
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test-secret", DATABASE=database, TESTING=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def rows_to_dicts(rows):
        return [dict(row) for row in rows]

    def current_user(db):
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return db.execute(
            "SELECT id, nickname, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    @app.get("/api/meetings")
    def get_meetings():
        keyword = request.args.get("keyword", "").strip()
        sport_id = request.args.get("sport_id", type=int)
        meeting_date = request.args.get("date", "").strip()
        location = request.args.get("location", "").strip()
        status = request.args.get("status", "").strip()

        if meeting_date:
            try:
                datetime.strptime(meeting_date, "%Y-%m-%d")
            except ValueError:
                return jsonify(message="날짜는 YYYY-MM-DD 형식이어야 합니다."), 400

        allowed = {"RECRUITING", "CLOSED", "COMPLETED", "CANCELED"}
        if status and status not in allowed:
            return jsonify(message="올바르지 않은 모집 상태입니다."), 400

        conditions, params = [], []
        if keyword:
            conditions.append("(m.title LIKE ? OR m.description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if sport_id is not None:
            conditions.append("m.sport_id = ?")
            params.append(sport_id)
        if meeting_date:
            conditions.append("m.meeting_date = ?")
            params.append(meeting_date)
        if location:
            conditions.append("m.location LIKE ?")
            params.append(f"%{location}%")
        if status:
            conditions.append("m.status = ?")
            params.append(status)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = """
            SELECT m.id, m.title, m.description, m.sport_id,
                   s.name AS sport_name, m.host_id, u.nickname AS host_name,
                   m.meeting_date, m.location, m.max_members, m.status
            FROM meetings m
            JOIN sports s ON s.id = m.sport_id
            JOIN users u ON u.id = m.host_id
        """ + where + " ORDER BY m.meeting_date ASC, m.id ASC"
        meetings = rows_to_dicts(get_db().execute(sql, params).fetchall())
        return jsonify(meetings=meetings, total=len(meetings))

    @app.get("/api/meetings/<int:meeting_id>")
    def get_meeting(meeting_id):
        row = get_db().execute(
            """
            SELECT m.id, m.title, m.description, m.sport_id,
                   s.name AS sport_name, m.host_id, u.nickname AS host_name,
                   m.meeting_date, m.location, m.max_members, m.status
            FROM meetings m
            JOIN sports s ON s.id = m.sport_id
            JOIN users u ON u.id = m.host_id
            WHERE m.id = ?
            """,
            (meeting_id,),
        ).fetchone()
        if row is None:
            return jsonify(message="모임을 찾을 수 없습니다."), 404
        return jsonify(dict(row))

    @app.post("/api/meetings")
    def create_meeting():
        user_id = session.get("user_id")
        if user_id is None:
            return jsonify(message="로그인이 필요합니다."), 401
        data = request.get_json(silent=True) or {}
        required = ["title", "description", "sport_id", "meeting_date", "location", "max_members"]
        missing = [key for key in required if data.get(key) in (None, "")]
        if missing:
            return jsonify(message=f"{missing[0]} 값이 필요합니다."), 400
        try:
            datetime.strptime(data["meeting_date"], "%Y-%m-%d")
        except ValueError:
            return jsonify(message="날짜는 YYYY-MM-DD 형식이어야 합니다."), 400
        db = get_db()
        sport = db.execute("SELECT id FROM sports WHERE id = ?", (data["sport_id"],)).fetchone()
        if sport is None:
            return jsonify(message="운동 종목을 찾을 수 없습니다."), 404
        cursor = db.execute(
            """
            INSERT INTO meetings
              (host_id, sport_id, title, description, meeting_date, location, max_members, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'RECRUITING')
            """,
            (user_id, data["sport_id"], data["title"], data["description"],
             data["meeting_date"], data["location"], data["max_members"]),
        )
        db.commit()
        return jsonify(message="모임이 생성되었습니다.", meeting_id=cursor.lastrowid), 201

    @app.put("/api/meetings/<int:meeting_id>")
    def update_meeting(meeting_id):
        db = get_db()
        user = current_user(db)
        if user is None:
            return jsonify(message="로그인이 필요합니다."), 401
        meeting = db.execute("SELECT id, host_id FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if meeting is None:
            return jsonify(message="모임을 찾을 수 없습니다."), 404
        if meeting["host_id"] != user["id"] and user["role"] != "ADMIN":
            return jsonify(message="수정 권한이 없습니다."), 403
        data = request.get_json(silent=True) or {}
        required = ["title", "description", "sport_id", "meeting_date", "location", "max_members", "status"]
        missing = [key for key in required if data.get(key) in (None, "")]
        if missing:
            return jsonify(message=f"{missing[0]} 값이 필요합니다."), 400
        try:
            datetime.strptime(data["meeting_date"], "%Y-%m-%d")
        except ValueError:
            return jsonify(message="날짜는 YYYY-MM-DD 형식이어야 합니다."), 400
        if data["status"] not in {"RECRUITING", "CLOSED", "COMPLETED", "CANCELED"}:
            return jsonify(message="올바르지 않은 모집 상태입니다."), 400
        db.execute(
            """
            UPDATE meetings SET title=?, description=?, sport_id=?, meeting_date=?,
              location=?, max_members=?, status=? WHERE id=?
            """,
            (data["title"], data["description"], data["sport_id"], data["meeting_date"],
             data["location"], data["max_members"], data["status"], meeting_id),
        )
        db.commit()
        return jsonify(message="모임이 수정되었습니다.")

    @app.delete("/api/meetings/<int:meeting_id>")
    def delete_meeting(meeting_id):
        db = get_db()
        user = current_user(db)
        if user is None:
            return jsonify(message="로그인이 필요합니다."), 401
        meeting = db.execute("SELECT id, host_id FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if meeting is None:
            return jsonify(message="모임을 찾을 수 없습니다."), 404
        if meeting["host_id"] != user["id"] and user["role"] != "ADMIN":
            return jsonify(message="삭제 권한이 없습니다."), 403
        db.execute("DELETE FROM meeting_members WHERE meeting_id = ?", (meeting_id,))
        db.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        db.commit()
        return "", 204

    @app.get("/api/users/me/meetings")
    def get_my_meetings():
        user_id = session.get("user_id")
        if user_id is None:
            return jsonify(message="로그인이 필요합니다."), 401
        rows = get_db().execute(
            """
            SELECT m.id, m.title, s.name AS sport_name, m.meeting_date,
                   m.location, m.max_members, m.status
            FROM meetings m JOIN sports s ON s.id = m.sport_id
            WHERE m.host_id = ? ORDER BY m.meeting_date ASC, m.id ASC
            """,
            (user_id,),
        ).fetchall()
        meetings = rows_to_dicts(rows)
        return jsonify(meetings=meetings, total=len(meetings))

    def init_db():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE users (
              id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, role TEXT NOT NULL
            );
            CREATE TABLE sports (
              id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE meetings (
              id INTEGER PRIMARY KEY AUTOINCREMENT, host_id INTEGER NOT NULL,
              sport_id INTEGER NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
              meeting_date TEXT NOT NULL, location TEXT NOT NULL,
              max_members INTEGER NOT NULL, status TEXT NOT NULL,
              FOREIGN KEY(host_id) REFERENCES users(id),
              FOREIGN KEY(sport_id) REFERENCES sports(id)
            );
            CREATE TABLE meeting_members (
              meeting_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
              PRIMARY KEY(meeting_id, user_id)
            );
            INSERT INTO users VALUES (1, '김규민', 'USER');
            INSERT INTO users VALUES (2, '관리자', 'ADMIN');
            INSERT INTO sports VALUES (1, '러닝');
            INSERT INTO sports VALUES (2, '풋살');
            INSERT INTO meetings
              (host_id, sport_id, title, description, meeting_date, location, max_members, status)
            VALUES
              (1, 1, '주말 한강 러닝', '초보자도 참여할 수 있습니다.', '2026-08-22', '여의도 한강공원', 10, 'RECRUITING'),
              (2, 2, '강남 주말 풋살', '즐겁게 풋살해요.', '2026-08-24', '서울 강남구', 12, 'CLOSED');
            """
        )
        db.commit()

    app.init_db = init_db
    return app

