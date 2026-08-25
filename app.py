import os

from dotenv import load_dotenv
from flask import Flask

from app.auth_gyumin.auth import auth_bp
from app.auth_gyumin.profile import uploads_bp
from app.auth_gyumin.user_sports import sports_bp
from app.auth_gyumin.users import users_bp
from app.meetings_gyudong.meetings import meetings_bp
from app.participation_euna.participation import participation_bp


load_dotenv()

app = Flask(__name__)

app.json.ensure_ascii = False

app.secret_key = os.getenv("SECRET_KEY")


app.register_blueprint(auth_bp) # auth.py에 있는 API들을 Flask 본체에 등록
app.register_blueprint(users_bp)
app.register_blueprint(sports_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(meetings_bp)
app.register_blueprint(participation_bp)

@app.get("/")
def home():
    return {
        "message": "meeting-api server is running"
    }, 200


if __name__ == "__main__":
    app.run(debug=True)
