from flask import Blueprint

bp = Blueprint('main', __name__)


@bp.route('/test_main')
def test_main():
    return "Main Blueprint Works!"
