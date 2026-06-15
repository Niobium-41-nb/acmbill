"""Tests for configuration module."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, _get_database_uri


class TestConfigDefaults:
    """Test default configuration values."""

    def test_secret_key_default(self):
        if 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        config = Config()
        assert config.SECRET_KEY == 'bill-management-secret-key-2024'

    def test_sqlalchemy_track_modifications(self):
        config = Config()
        assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_max_content_length(self):
        config = Config()
        assert config.MAX_CONTENT_LENGTH == 50 * 1024 * 1024  # 50MB

    def test_allowed_extensions(self):
        config = Config()
        allowed = config.ALLOWED_EXTENSIONS
        assert 'pdf' in allowed
        assert 'png' in allowed
        assert 'jpg' in allowed
        assert 'doc' in allowed
        assert 'xlsx' in allowed
        assert len(allowed) == 11

    def test_mail_server_default(self, monkeypatch):
        monkeypatch.delenv('MAIL_SERVER', raising=False)
        config = Config()
        assert config.MAIL_SERVER == 'smtp.qq.com'

    def test_mail_port_default(self, monkeypatch):
        monkeypatch.delenv('MAIL_PORT', raising=False)
        config = Config()
        assert config.MAIL_PORT == 587

    def test_mail_use_tls_default(self, monkeypatch):
        monkeypatch.delenv('MAIL_USE_TLS', raising=False)
        config = Config()
        assert config.MAIL_USE_TLS is True

    def test_mail_use_ssl_default(self, monkeypatch):
        monkeypatch.delenv('MAIL_USE_SSL', raising=False)
        config = Config()
        assert config.MAIL_USE_SSL is False


class TestDatabaseUri:
    """Test database URI construction."""

    def test_get_database_uri_with_env_vars(self, monkeypatch):
        monkeypatch.setenv('DB_HOST', 'localhost')
        monkeypatch.setenv('DB_PORT', '3306')
        monkeypatch.setenv('DB_USER', 'testuser')
        monkeypatch.setenv('DB_PASSWORD', 'testpass')
        monkeypatch.setenv('DB_NAME', 'testdb')
        uri = _get_database_uri()
        assert 'mysql+pymysql://' in uri
        assert 'testuser:testpass@localhost:3306/testdb' in uri
        assert 'charset=utf8mb4' in uri

    def test_get_database_uri_fallback_to_sqlite(self, monkeypatch):
        for key in ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']:
            monkeypatch.delenv(key, raising=False)
        uri = _get_database_uri()
        assert uri.startswith('sqlite:///')
        assert 'bill.db' in uri


class TestAppCreation:
    """Test application factory."""

    def test_app_creation(self, app):
        assert app is not None
        assert app.config['TESTING'] is True

    def test_app_has_blueprints(self, app):
        rules = [rule.endpoint for rule in app.url_map.iter_rules()]
        assert any('auth.' in r for r in rules), "Auth blueprint not registered"
        assert any('project.' in r for r in rules), "Project blueprint not registered"

    def test_index_redirects(self, client):
        response = client.get('/')
        assert response.status_code in (301, 302, 308)

    def test_404_page(self, client):
        response = client.get('/nonexistent')
        assert response.status_code == 404
