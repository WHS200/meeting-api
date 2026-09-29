from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address, # 누구의 요청인지 구분할 때 IP 주소를 사용
    # get_remote_address()는 Flask의 request.remote_addr 값을 반환

    storage_uri="memory://" # 카운터를 현재 서버 프로세스의 메모리에 저장
    # e.g.
    # 1.2.3.4 → login 4회
    # 5.6.7.8 → login 2회
    # 이런 정보가 메모리에 존재
)