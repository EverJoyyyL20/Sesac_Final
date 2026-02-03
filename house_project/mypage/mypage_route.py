import os
from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

mypage_bp = Blueprint('mypage', __name__, template_folder='.')

# 사진이 저장될 경로 설정
UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@mypage_bp.route('/mypage', methods=['GET', 'POST'])
def mypage():
    if request.method == 'POST':
        # 닉네임, 소개글 가져오기
        nickname = request.form.get('nickname')
        bio = request.form.get('bio')
        
        # 이미지 파일 가져오기
        file = request.files.get('profile_img')
        if file and file.filename != '':
            # 보안을 위해 파일명 정제 (파일명에 이상한 경로가 섞이지 않게)
            filename = secure_filename(f"user_1_{file.filename}") 
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            print(f"이미지 저장 완료: {filename}")

        print(f"프로필 업데이트: {nickname}, {bio}")
        return redirect(url_for('mypage.mypage'))

    return render_template('mypage.html')
@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    # GET 방식이므로 폼 데이터가 아닌 DB에서 가져온 기본값을 넣어줘야 합니다 (임시값 설정)
    return render_template('edit_profile.html', nickname="현재닉네임", bio="현재소개")

@mypage_bp.route('/update', methods=['POST'])
def update_profile():  # HTML form의 action과 일치해야 함
    nickname = request.form.get('nickname')
    bio = request.form.get('bio')
    
    # 이미지 처리 로직 (기존 코드 유지)
    file = request.files.get('profile_img')
    if file and file.filename != '':
        filename = secure_filename(f"user_1_{file.filename}") 
        # 폴더가 없으면 에러날 수 있으니 확인 필요
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

    print(f"업데이트 완료: {nickname}, {bio}")
    return redirect(url_for('mypage.mypage'))