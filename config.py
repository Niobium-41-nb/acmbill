import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _get_database_uri():
    """从环境变量构建数据库连接URI，优先使用MySQL"""
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '3306')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    if db_host and db_user and db_password and db_name:
        return f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4'

    # 回退到 SQLite
    return 'sqlite:///' + os.path.join(basedir, 'bill.db')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bill-management-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}

    # 邮箱配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.qq.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or ''  # 发件邮箱地址
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or ''  # 邮箱授权码
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or ''  # 发件人
