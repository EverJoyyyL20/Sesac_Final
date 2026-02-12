import os
import urllib.parse
from pymongo import MongoClient
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

oauth = OAuth()
# 1. .env 파일의 환경 변수 로드
load_dotenv()

# 2. os.getenv를 통해 정보 가져오기
username = os.getenv("MONGO_USER")
password = os.getenv("MONGO_PASS")
cluster_addr = os.getenv("MONGO_CLUSTER")

# 3. 보안을 위한 패스워드 인코딩
encoded_password = urllib.parse.quote_plus(password)

# 4. MongoDB 연결 URI 구성
uri = f"mongodb+srv://{username}:{encoded_password}@{cluster_addr}/?appName=Cluster0&tlsAllowInvalidCertificates=true"

try:
    client = MongoClient(uri)
    db = client['sesac_final']
    
    # 다른 파일에서 불러다 쓸 컬렉션들
    users_col = db['user']
    infra_col = db['infra']
    houses_col = db['properties_test2']

    print("✅ MongoDB 접속 성공! (환경 변수 사용)",houses_col.count_documents({}))
except Exception as e:
    print("❌ MongoDB 접속 실패:", e)