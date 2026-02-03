from flask import Blueprint, render_template


mypage_bp = Blueprint('mypage', __name__, template_folder='.')

@mypage_bp.route('/mypage')
def mypage():
    return render_template('mypage.html')