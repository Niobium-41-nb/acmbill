"""pytest fixtures for the bill management application.

Uses session-scoped app with per-test database reset via drop_all/create_all.
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════
# Speed up password hashing for tests (scrypt is too slow)
# ═══════════════════════════════════════════════════════════════════
from werkzeug.security import generate_password_hash as _original_generate, check_password_hash


def _fast_password_hash(password):
    """Use sha256 instead of scrypt for faster tests."""
    return _original_generate(password, method='pbkdf2:sha256:1000')


@pytest.fixture(autouse=True, scope='session')
def _patch_password_hashing():
    """Replace slow scrypt hashing with fast pbkdf2 for all tests."""
    import models
    original_set_password = models.User.set_password
    models.User.set_password = lambda self, pw: setattr(
        self, 'password_hash', _fast_password_hash(pw)
    )
    yield
    models.User.set_password = original_set_password
# ═══════════════════════════════════════════════════════════════════


from app import create_app, _create_default_admin
from models import db as _db, User, Project, TeamMember, ReimbursementItem, ProjectFile


@pytest.fixture(scope='session')
def app():
    """Create a Flask application shared across all tests (session-scoped)."""
    os.environ['FLASK_TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
        'UPLOAD_FOLDER': tempfile.mkdtemp(prefix='bill_test_uploads_'),
    })

    yield app

    import shutil
    upload_dir = app.config.get('UPLOAD_FOLDER', '')
    if upload_dir and os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture
def db(app):
    """Reset database before each test and provide session."""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        _create_default_admin()
        yield _db
        _db.session.rollback()
        _db.session.remove()


@pytest.fixture
def client(app, db):
    """Provide a Flask test client (depends on db to ensure DB reset)."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Provide a Flask CLI runner."""
    return app.test_cli_runner()


# ── User fixtures ──────────────────────────────────────────────

@pytest.fixture
def admin_user(app, db):
    """Get the default admin user created by _create_default_admin()."""
    admin = User.query.filter_by(username='admin').first()
    assert admin is not None, "Default admin not found"
    return admin


@pytest.fixture
def normal_user(app, db):
    """Create a normal user in the test database."""
    user = User(
        username='testuser',
        email='user@test.com',
        email_verified=True,
        role='user',
        real_name='测试用户',
        student_id='2024001',
        student_class='计算机2401班'
    )
    user.set_password('user123')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def second_user(app, db):
    """Create a second normal user for team tests."""
    user = User(
        username='testuser2',
        email='user2@test.com',
        email_verified=True,
        role='user',
        real_name='测试用户2',
        student_id='2024002',
        student_class='计算机2401班'
    )
    user.set_password('user456')
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def third_user(app, db):
    """Create a third normal user for team limit tests."""
    user = User(
        username='testuser3',
        email='user3@test.com',
        email_verified=True,
        role='user',
        real_name='测试用户3',
        student_id='2024003',
        student_class='计算机2402班'
    )
    user.set_password('user789')
    _db.session.add(user)
    _db.session.commit()
    return user


# ── Login helpers ──────────────────────────────────────────────

def login(client, username, password):
    """Helper to log in via POST."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


# ── Project / data fixtures ────────────────────────────────────

@pytest.fixture
def project(app, db, normal_user):
    """Create a project owned by normal_user."""
    p = Project(
        title='测试项目',
        description='这是一个测试项目',
        competition_name='ICPC邀请赛',
        competition_date='2026-05-01',
        status='draft',
        owner_id=normal_user.id
    )
    _db.session.add(p)
    _db.session.commit()
    return p


@pytest.fixture
def item(app, db, project):
    """Create a reimbursement item."""
    item = ReimbursementItem(
        project_id=project.id,
        teacher='章英、李嘉位',
        reimbursement_date='2026-05-01',
        expense_category='住宿费',
        content='住宿费',
        amount=1440.00,
        applicant='刘泽成',
        student_id='2024317240106',
        student_class='信科2401班'
    )
    _db.session.add(item)
    _db.session.commit()
    return item
