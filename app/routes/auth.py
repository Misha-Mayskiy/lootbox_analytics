from flask import Blueprint

bp = Blueprint('auth', __name__)


@bp.route('/test_auth')
def test_auth():
    return "Auth Blueprint Works!"
