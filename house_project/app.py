import os
from flask import Flask
from main.main_route import main_bp
from auth.auth_route import auth_bp
from mypage.mypage_route import mypage_bp
from database import users_col

app = Flask(__name__)

app.register_blueprint(mypage_bp)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_key_for_safety')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
    