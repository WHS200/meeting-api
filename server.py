import os

from dotenv import load_dotenv
from flask import Flask, redirect
from flask_socketio import SocketIO

from werkzeug.middleware.proxy_fix import ProxyFix
# ProxyFix: Nginx가 전달해주는 실제 클라이언트 IP 정보를 Flask가 올바르게 해석할 수 있게 해줌.
from app.shared.rate_limiter import limiter

from app.auth_gyumin.auth import auth_bp
from app.auth_gyumin.profile import uploads_bp
from app.auth_gyumin.user_sports import sports_bp
from app.auth_gyumin.users import users_bp
from app.chat_dahyun import chat_bp, register_socket_events
from app.meetings_gyudong.meetings import meetings_bp
from app.participation_euna.participation import participation_bp
from app.codex_features import features_bp


load_dotenv()

app = Flask(__name__)

### rate limit 설정
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1 # 1: Flask 앞에 신뢰하는 proxy 1개가 있다.
)

limiter.init_app(app) # 미리 만들어 둔 limiter 객체를 이 Flask app에서 사용
###

app.json.ensure_ascii = False

app.secret_key = os.getenv("SECRET_KEY")
socketio = SocketIO(app)


app.register_blueprint(auth_bp) # auth.py에 있는 API들을 Flask 본체에 등록
app.register_blueprint(users_bp)
app.register_blueprint(sports_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(meetings_bp)
app.register_blueprint(participation_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(features_bp)

register_socket_events(socketio)

@app.get("/")
def home():
    return redirect("/static/index.html") # 사이트 들어가자마자 바로 /index.html 보이게

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return {"message": "Too many requests. Please try again later."}, 429


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True)
