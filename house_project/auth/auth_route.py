from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint('auth', __name__,template_folder='.')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password') 
        VALID_EMAIL = "test@email.com"
        VALID_PASSWORD = "password123!"
        if email == VALID_EMAIL and password == VALID_PASSWORD:
            session['user_id'] = email
            session['nickname'] = "테스트유저"
            return redirect(url_for('main.index'))
        else:
            return "<script>alert('이메일 또는 비밀번호가 틀렸습니다.'); history.back();</script>"
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('auth.login'))
    return render_template('register.html')