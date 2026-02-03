from flask import Flask
from routes.main_route import main_bp
from routes.auth_route import auth_bp
from routes.mypage_route import mypage_bp

app = Flask(__name__)

app.register_blueprint(mypage_bp)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True)