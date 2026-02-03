from flask import Blueprint, render_template, request, redirect, url_for, session
import os
from werkzeug.utils import secure_filename

mypage_bp = Blueprint('mypage', __name__, template_folder='.')

UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    # 파일명에 '.'이 있고, 확장자를 추출해서 소문자로 변환한 뒤 목록에 있는지 확인
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@mypage_bp.route('/mypage')
def mypage():
    # 1. 로그인 여부 확인
    if 'user_id' not in session:
        return redirect(url_for('auth.login')) # 로그인 안 됐으면 로그인창으로

    # 2. 세션에서 정보 가져오기 (실제로는 여기서 DB 조회를 합니다)
    user_email = session.get('user_id')
    # 임시로 세션이나 DB 대신 현재는 로직 확인을 위해 변수화
    nickname = session.get('nickname', '설정된 닉네임이 없습니다.')
    bio = session.get('bio', '소개글을 등록해 보세요.')
    profile_img = session.get('profile_img')

    return render_template('mypage.html', 
                           user_email=user_email, 
                           nickname=nickname, 
                           bio=bio, 
                           profile_img=profile_img)

@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 수정 페이지 들어갈 때 기존 값을 채워넣어줌
    return render_template('edit_profile.html', 
                           nickname=session.get('nickname', ''), 
                           bio=session.get('bio', ''))

@mypage_bp.route('/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    new_nickname = request.form.get('nickname')
    new_bio = request.form.get('bio')
    
    session['nickname'] = new_nickname
    session['bio'] = new_bio

    file = request.files.get('profile_img')
    
    if file and file.filename != '':
        if allowed_file(file.filename): 
            filename = secure_filename(f"user_{session['user_id']}_{file.filename}") 
            
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
                
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            session['profile_img'] = url_for('static', filename=f'profile_pics/{filename}')
        else:
            # 허용되지 않은 파일 형식일 경우 처리 (선택 사항)
            print("허용되지 않는 파일 형식입니다.")
            # return "허용되지 않는 파일 형식입니다.", 400 등의 처리가 가능합니다.

    return redirect(url_for('mypage.mypage'))