import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import Config
from models import db, User

# 加载 .env 文件中的环境变量
load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'info'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)

    # 注册蓝图
    from auth import auth_bp
    from project import project_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(project_bp)

    # 首页重定向
    @app.route('/')
    def index():
        return redirect(url_for('project.dashboard'))

    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 创建数据库表
    with app.app_context():
        db.create_all()
        # 创建默认管理员
        _create_default_admin()

    return app


def _create_default_admin():
    """创建默认管理员账号（从环境变量读取配置）"""
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            email=admin_email,
            email_verified=True,
            role='admin',
            real_name='系统管理员'
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f'默认管理员账号已创建: {admin_username} / {admin_password}')


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=1444, debug=True)
