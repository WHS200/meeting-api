FROM python:3.11.5-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "1", "--threads", "100", "-b", "0.0.0.0:5000", "server:app"]
# server : app
#  │     │
#  │     └─ server.py 안에 있는 변수 app
#  │
#  └─ server.py 파일, 정확히는 Python 모듈 app
# => server.py를 불러와서 그 안의 app이라는 Flask 객체를 실행