import os
from flask import Flask
from dotenv import load_dotenv
from main.main_route import main_bp
from auth.auth_route import auth_bp
from mypage.mypage_route import mypage_bp
# database.py에서 oauth 객체를 가져옵니다.
from database import oauth 
import os
# 로컬 테스트 시 http 허용 (배포 시에는 삭제하거나 0으로 변경)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# 1. .env 로드
load_dotenv()

app = Flask(__name__)

# 2. Flask 설정
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_key_for_safety')

# 3. OAuth 초기화 (database.py에 있는 oauth 객체를 이 app과 연결)
oauth.init_app(app)

# 4. 구글 서비스 등록
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# 5. 블루프린트 등록
app.register_blueprint(mypage_bp)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)