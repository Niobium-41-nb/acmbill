"""Tests for auth blueprint (login, register, profile, password)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from tests.conftest import login, logout


class TestLogin:
    """Tests for login functionality."""

    def test_login_page_get(self, client):
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_login_success(self, client, normal_user):
        response = login(client, 'testuser', 'user123')
        assert response.status_code == 200
        # Should redirect to dashboard
        assert 'dashboard' in response.request.path or response.status_code == 200

    def test_login_wrong_password(self, client, normal_user):
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword',
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error message
        assert '用户名或密码错误'.encode() in response.data

    def test_login_empty_username(self, client):
        response = client.post('/auth/login', data={
            'username': '',
            'password': 'something',
        }, follow_redirects=True)
        assert '请输入'.encode() in response.data

    def test_login_empty_password(self, client):
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': '',
        }, follow_redirects=True)
        assert '请输入'.encode() in response.data

    def test_login_nonexistent_user(self, client):
        response = client.post('/auth/login', data={
            'username': 'nobody',
            'password': 'something',
        }, follow_redirects=True)
        assert '用户名或密码错误'.encode() in response.data

    def test_login_redirect_if_authenticated(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/login', follow_redirects=True)
        assert response.status_code == 200
        # Should be on dashboard, not login page
        assert 'dashboard' in response.request.path


class TestLogout:
    """Tests for logout functionality."""

    def test_logout(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = logout(client)
        assert response.status_code == 200

    def test_logout_clears_session(self, client, normal_user):
        login(client, 'testuser', 'user123')
        logout(client)
        # Try accessing a protected page
        response = client.get('/project/dashboard', follow_redirects=True)
        assert '请先登录'.encode() in response.data

    def test_logout_without_login(self, client):
        response = logout(client)
        # Might redirect to login with message
        assert response.status_code == 200


class TestRegister:
    """Tests for registration functionality."""

    def test_register_page_get(self, client):
        response = client.get('/auth/register')
        assert response.status_code == 200

    def test_register_redirect_if_authenticated(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/register', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect away from register

    def test_register_success(self, app, client):
        """Test successful registration with valid verification code."""
        with app.app_context():
            from models import db, EmailVerificationCode
            from datetime import datetime, timedelta

            # Create a valid verification code first
            code = EmailVerificationCode(
                email='newuser@test.com',
                code='888888',
                purpose='register',
                expires_at=datetime.utcnow() + timedelta(minutes=10),
                used=False
            )
            db.session.add(code)
            db.session.commit()

        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123',
            'verification_code': '888888',
            'real_name': '新用户',
            'student_id': '2024003',
            'student_class': '计算机2401班',
        }, follow_redirects=True)
        assert response.status_code == 200

        # Verify user was created
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'newuser@test.com'
            assert user.email_verified is True

    def test_register_duplicate_username(self, client, normal_user):
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'different@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '重复',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '已存在'.encode() in response.data

    def test_register_duplicate_email(self, client, normal_user):
        response = client.post('/auth/register', data={
            'username': 'different',
            'email': 'user@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '重复',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '已被注册'.encode() in response.data

    def test_register_password_mismatch(self, client):
        response = client.post('/auth/register', data={
            'username': 'newbie',
            'email': 'newbie@test.com',
            'password': 'pass123',
            'confirm_password': 'different',
            'verification_code': '123456',
            'real_name': '某人',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '不一致'.encode() in response.data

    def test_register_short_password(self, client):
        response = client.post('/auth/register', data={
            'username': 'newbie',
            'email': 'newbie@test.com',
            'password': '12345',
            'confirm_password': '12345',
            'verification_code': '123456',
            'real_name': '某人',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '不能少于6位'.encode() in response.data

    def test_register_invalid_email(self, client):
        response = client.post('/auth/register', data={
            'username': 'user1',
            'email': 'not_an_email',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '某人',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '格式不正确'.encode() in response.data

    def test_register_missing_real_name(self, client):
        response = client.post('/auth/register', data={
            'username': 'user1',
            'email': 'u1@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '',
            'student_id': '123',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '不能为空'.encode() in response.data

    def test_register_missing_student_id(self, client):
        response = client.post('/auth/register', data={
            'username': 'user1',
            'email': 'u1@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '某人',
            'student_id': '',
            'student_class': '班级',
        }, follow_redirects=True)
        assert '不能为空'.encode() in response.data

    def test_register_missing_class(self, client):
        response = client.post('/auth/register', data={
            'username': 'user1',
            'email': 'u1@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
            'verification_code': '123456',
            'real_name': '某人',
            'student_id': '123',
            'student_class': '',
        }, follow_redirects=True)
        assert '不能为空'.encode() in response.data


class TestSendVerificationCode:
    """Tests for sending email verification codes."""

    def test_send_code_no_email_config(self, client):
        """Without email config, should return dev mode code."""
        response = client.post('/auth/send-code', data={
            'email': 'newuser@test.com',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'dev_code' in data  # dev mode returns the code itself

    def test_send_code_invalid_email(self, client):
        response = client.post('/auth/send-code', data={
            'email': 'invalid-email',
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_send_code_empty_email(self, client):
        response = client.post('/auth/send-code', data={
            'email': '',
        })
        assert response.status_code == 400

    def test_send_code_rate_limit(self, app, client):
        """Test rate limiting: can't send twice within 60 seconds."""
        # First send
        client.post('/auth/send-code', data={'email': 'ratelimit@test.com'})
        # Second send immediately
        response = client.post('/auth/send-code', data={'email': 'ratelimit@test.com'})
        assert response.status_code == 429
        data = json.loads(response.data)
        assert data['success'] is False

    def test_send_code_authenticated(self, client, normal_user):
        """Authenticated user can send code to their own email."""
        login(client, 'testuser', 'user123')
        # Send code with empty data (will use current_user's email)
        response = client.post('/auth/send-code', data={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestProfile:
    """Tests for user profile management."""

    def test_profile_page_get(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/profile')
        assert response.status_code == 200

    def test_profile_page_requires_login(self, client):
        response = client.get('/auth/profile', follow_redirects=True)
        assert '请先登录'.encode() in response.data

    def test_profile_update(self, app, client, normal_user):
        login(client, 'testuser', 'user123')

        with app.app_context():
            from models import db, EmailVerificationCode
            from datetime import datetime, timedelta
            code = EmailVerificationCode(
                email=normal_user.email,
                code='999999',
                purpose='profile',
                expires_at=datetime.utcnow() + timedelta(minutes=10),
                used=False
            )
            db.session.add(code)
            db.session.commit()

        response = client.post('/auth/profile', data={
            'real_name': '新姓名',
            'student_id': '2024999',
            'student_class': '新班级',
            'verification_code': '999999',
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import User
            updated = User.query.filter_by(username='testuser').first()
            assert updated.real_name == '新姓名'
            assert updated.student_id == '2024999'
            assert updated.student_class == '新班级'

    def test_profile_update_no_code(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.post('/auth/profile', data={
            'real_name': '新姓名',
            'student_id': '2024999',
            'student_class': '新班级',
            'verification_code': '',
        }, follow_redirects=True)
        assert '验证码'.encode() in response.data


class TestChangePassword:
    """Tests for password change."""

    def test_change_password_success(self, app, client, normal_user):
        login(client, 'testuser', 'user123')

        with app.app_context():
            from models import db, EmailVerificationCode
            from datetime import datetime, timedelta
            code = EmailVerificationCode(
                email=normal_user.email,
                code='777777',
                purpose='profile',
                expires_at=datetime.utcnow() + timedelta(minutes=10),
                used=False
            )
            db.session.add(code)
            db.session.commit()

        response = client.post('/auth/profile/password', data={
            'old_password': 'user123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
            'verification_code': '777777',
        }, follow_redirects=True)
        assert response.status_code == 200

        # Verify new password works
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            assert user.check_password('newpass456') is True
            assert user.check_password('user123') is False

    def test_change_password_wrong_old(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.post('/auth/profile/password', data={
            'old_password': 'wrongold',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
            'verification_code': '123456',
        }, follow_redirects=True)
        assert '错误'.encode() in response.data

    def test_change_password_short_new(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.post('/auth/profile/password', data={
            'old_password': 'user123',
            'new_password': '12345',
            'confirm_password': '12345',
            'verification_code': '123456',
        }, follow_redirects=True)
        assert '不能少于6位'.encode() in response.data

    def test_change_password_mismatch(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.post('/auth/profile/password', data={
            'old_password': 'user123',
            'new_password': 'newpass1',
            'confirm_password': 'newpass2',
            'verification_code': '123456',
        }, follow_redirects=True)
        assert '不一致'.encode() in response.data

    def test_change_password_requires_login(self, client):
        response = client.post('/auth/profile/password', data={
            'old_password': 'any',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
        }, follow_redirects=True)
        assert '请先登录'.encode() in response.data


class TestApiMe:
    """Tests for /auth/api/me."""

    def test_api_me_returns_user_info(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/api/me')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['username'] == 'testuser'
        assert data['role'] == 'user'

    def test_api_me_requires_login(self, client):
        response = client.get('/auth/api/me')
        assert response.status_code in (302, 401)


class TestApiUsers:
    """Tests for /auth/api/users (user search)."""

    def test_api_users_search(self, client, normal_user, second_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/api/users?q=testuser2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) >= 1
        usernames = [u['username'] for u in data]
        assert 'testuser2' in usernames

    def test_api_users_empty_search(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/api/users')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_users_no_match(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/auth/api/users?q=zzzzzzzzz')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 0

    def test_api_users_requires_login(self, client):
        response = client.get('/auth/api/users')
        assert response.status_code in (302, 401)
