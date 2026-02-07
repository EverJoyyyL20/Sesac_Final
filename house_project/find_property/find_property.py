import os
from flask import Blueprint, render_template,current_app
from dotenv import load_dotenv

load_dotenv()

find_property_bp = Blueprint('find_property', __name__, template_folder='.')

@find_property_bp.route('/find-property')
def find_property():
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    return render_template('find_property.html', client_id=client_id)