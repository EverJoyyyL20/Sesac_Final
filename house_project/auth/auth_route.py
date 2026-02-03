from flask import Blueprint, render_template, request, redirect, url_for

auth_bp = Blueprint('auth', __name__, template_folder='.')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('main.index'))
    return render_template('login.html')

@auth_bp.route('/register')
def register():
    return render_template('register.html')

@auth_bp.route('/login/google')
def google_login():
    return "구글 로그인 API 연결이 필요합니다 (준비 중)"