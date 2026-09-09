from flask import Blueprint, request, session
from app.shared.decorators import login_required
from .helpers import APIError, body, choice, pagination, role_for, text_field, transaction

community_bp = Blueprint("community", __name__, url_prefix="/api/community")
BOARDS = ("FREE", "TIPS", "NOTICE")


def get_post(cursor, post_id, lock=False):
    cursor.execute("""SELECT p.*, u.nickname AS author_nickname FROM community_posts p
        JOIN users u ON u.user_id = p.author_id
        WHERE p.post_id = %s AND p.deleted_at IS NULL""" + (" FOR UPDATE" if lock else ""), (post_id,))
    post = cursor.fetchone()
    if post is None:
        raise APIError("Post not found.", 404)
    return post


def can_edit(cursor, author_id):
    if author_id != session["user_id"] and role_for(cursor, session["user_id"]) != "ADMIN":
        raise APIError("Not authorized.", 403)


@community_bp.get("/posts")
@login_required
def list_posts():
    board = request.args.get("board", "")
    if board:
        choice(board, BOARDS, "board")
    keyword = request.args.get("keyword", "").strip()
    if len(keyword) > 100:
        raise APIError("keyword too long.")
    with transaction() as cursor:
        cursor.execute("""SELECT p.post_id, p.author_id, p.board, p.title, p.created_at,
            u.nickname AS author_nickname FROM community_posts p JOIN users u ON u.user_id = p.author_id
            WHERE p.deleted_at IS NULL AND (%s = '' OR p.board = %s)
            AND (p.title LIKE %s OR p.content LIKE %s)
            ORDER BY p.post_id DESC LIMIT %s OFFSET %s""",
            (board, board, f"%{keyword}%", f"%{keyword}%", *pagination()))
        return {"posts": cursor.fetchall()}


@community_bp.get("/posts/<int:post_id>")
@login_required
def post_detail(post_id):
    with transaction() as cursor:
        post = get_post(cursor, post_id)
        cursor.execute("""SELECT c.comment_id, c.author_id, c.content, c.created_at,
            u.nickname AS author_nickname FROM community_comments c JOIN users u ON u.user_id = c.author_id
            WHERE c.post_id = %s AND c.deleted_at IS NULL ORDER BY c.comment_id
            LIMIT %s OFFSET %s""", (post_id, *pagination()))
        return {"post": post, "comments": cursor.fetchall()}


def post_input(data):
    return (choice(data.get("board"), BOARDS, "board"), text_field(data, "title", 2, 100),
            text_field(data, "content", 1, 10000))


@community_bp.post("/posts")
@login_required
def create_post():
    board, title, content = post_input(body())
    with transaction() as cursor:
        if board == "NOTICE" and role_for(cursor, session["user_id"]) != "ADMIN":
            raise APIError("Only ADMIN can write NOTICE.", 403)
        cursor.execute("INSERT INTO community_posts (author_id, board, title, content) VALUES (%s, %s, %s, %s)",
                       (session["user_id"], board, title, content))
        post_id = cursor.lastrowid
    return {"post_id": post_id}, 201


@community_bp.put("/posts/<int:post_id>")
@login_required
def update_post(post_id):
    board, title, content = post_input(body())
    with transaction() as cursor:
        post = get_post(cursor, post_id, lock=True)
        can_edit(cursor, post["author_id"])
        if (board == "NOTICE" or post["board"] == "NOTICE") and role_for(cursor, session["user_id"]) != "ADMIN":
            raise APIError("Only ADMIN can edit NOTICE.", 403)
        cursor.execute("UPDATE community_posts SET board = %s, title = %s, content = %s WHERE post_id = %s",
                       (board, title, content, post_id))
    return {"message": "Post updated."}


@community_bp.delete("/posts/<int:post_id>")
@login_required
def delete_post(post_id):
    with transaction() as cursor:
        post = get_post(cursor, post_id, lock=True)
        can_edit(cursor, post["author_id"])
        cursor.execute("UPDATE community_posts SET deleted_at = CURRENT_TIMESTAMP() WHERE post_id = %s", (post_id,))
    return "", 204


@community_bp.post("/posts/<int:post_id>/comments")
@login_required
def create_comment(post_id):
    content = text_field(body(), "content", 1, 1000)
    with transaction() as cursor:
        get_post(cursor, post_id, lock=True)
        cursor.execute("INSERT INTO community_comments (post_id, author_id, content) VALUES (%s, %s, %s)",
                       (post_id, session["user_id"], content))
        comment_id = cursor.lastrowid
    return {"comment_id": comment_id}, 201


@community_bp.delete("/comments/<int:comment_id>")
@login_required
def delete_comment(comment_id):
    with transaction() as cursor:
        cursor.execute("SELECT author_id FROM community_comments WHERE comment_id = %s AND deleted_at IS NULL FOR UPDATE", (comment_id,))
        comment = cursor.fetchone()
        if not comment:
            raise APIError("Comment not found.", 404)
        can_edit(cursor, comment["author_id"])
        cursor.execute("UPDATE community_comments SET deleted_at = CURRENT_TIMESTAMP() WHERE comment_id = %s", (comment_id,))
    return "", 204
