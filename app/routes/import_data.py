from flask import Blueprint

bp = Blueprint('import_data', __name__)


@bp.route('/test_import')
def test_import():
    return "Import Data Blueprint Works!"
