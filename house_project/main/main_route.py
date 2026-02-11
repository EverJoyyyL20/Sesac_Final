from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from database import users_col  # 이전에 만든 database.py에서 가져옴
import random
import string
from datetime import datetime

main_bp = Blueprint('main', __name__, template_folder='.')


@main_bp.route('/')
def index():
    return render_template('main.html')