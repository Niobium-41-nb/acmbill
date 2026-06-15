import smtplib
import re
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, EmailVerificationCode

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def send_email(to_email, subject, body):
    """发送邮件"""
    mail_config = current_app.config
    smtp_server = mail_config.get('MAIL_SERVER', 'smtp.qq.com')
    smtp_port = mail_config.get('MAIL_PORT', 587)
    use_tls = mail_config.get('MAIL_USE_TLS', True)
    use_ssl = mail_config.get('MAIL_USE_SSL', False)
    username = mail_config.get('MAIL_USERNAME', '')
    password = mail_config.get('MAIL_PASSWORD', '')
    sender = mail_config.get('MAIL_DEFAULT_SENDER', username)

    if not username or not password:
        return False

    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_email

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()
        server.login(username, password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        current_app.logger.error(f'邮件发送失败: {str(e)}')
        return False


def send_verification_code_email(to_email, code):
    """发送验证码邮件"""
    subject = '报销材料管理系统 - 邮箱验证码'
    body = f'''
    <div style="max-width:600px;margin:0 auto;padding:20px;font-family:Arial,sans-serif;">
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px;border-radius:10px 10px 0 0;text-align:center;">
            <h2 style="color:white;margin:0;">报销材料管理系统</h2>
        </div>
        <div style="background:#f9f9f9;padding:30px;border-radius:0 0 10px 10px;border:1px solid #eee;">
            <p style="font-size:16px;color:#333;">您好！</p>
            <p style="font-size:16px;color:#333;">您正在进行邮箱验证，验证码如下：</p>
            <div style="text-align:center;margin:30px 0;">
                <span style="font-size:36px;font-weight:bold;color:#667eea;letter-spacing:8px;background:#f0f0ff;padding:15px 30px;border-radius:8px;">{code}</span>
            </div>
            <p style="font-size:14px;color:#999;">验证码有效期为10分钟，请尽快完成验证。</p>
            <p style="font-size:14px;color:#999;">如果这不是您本人的操作，请忽略此邮件。</p>
        </div>
        <div style="text-align:center;padding:15px;color:#999;font-size:12px;">
            <p>此邮件由系统自动发送，请勿回复</p>
        </div>
    </div>
    '''
    return send_email(to_email, subject, body)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('project.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'欢迎回来，{user.real_name or user.username}！', 'success')
            return redirect(next_page or url_for('project.dashboard'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('project.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        verification_code = request.form.get('verification_code', '').strip()
        real_name = request.form.get('real_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        student_class = request.form.get('student_class', '').strip()

        # 验证
        if not username or not password or not email:
            flash('用户名、邮箱和密码不能为空', 'danger')
            return render_template('register.html')

        if not real_name:
            flash('真实姓名不能为空', 'danger')
            return render_template('register.html')

        if not student_id:
            flash('学号不能为空', 'danger')
            return render_template('register.html')

        if not student_class:
            flash('班级不能为空', 'danger')
            return render_template('register.html')

        if not EMAIL_REGEX.match(email):
            flash('邮箱格式不正确', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('两次密码输入不一致', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('密码长度不能少于6位', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('该邮箱已被注册', 'danger')
            return render_template('register.html')

        # 验证邮箱验证码
        if not verification_code:
            flash('请输入邮箱验证码', 'danger')
            return render_template('register.html')

        # 查找有效的验证码
        valid_code = EmailVerificationCode.query.filter_by(
            email=email,
            code=verification_code,
            purpose='register',
            used=False
        ).order_by(EmailVerificationCode.created_at.desc()).first()

        if not valid_code:
            flash('验证码无效', 'danger')
            return render_template('register.html')

        if valid_code.is_expired():
            flash('验证码已过期，请重新获取', 'danger')
            return render_template('register.html')

        # 标记验证码已使用
        valid_code.used = True

        # 创建用户
        user = User(
            username=username,
            email=email,
            email_verified=True,
            role='user',
            real_name=real_name,
            student_id=student_id,
            student_class=student_class
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    """发送邮箱验证码"""
    # 如果用户已登录，优先使用当前用户的邮箱
    if current_user.is_authenticated:
        email = current_user.email
        purpose = 'profile'  # 个人信息修改场景
    else:
        # 支持 JSON 和 form-data 两种格式
        if request.is_json:
            email = request.json.get('email', '').strip()
        else:
            email = request.form.get('email', '').strip()
        purpose = 'register'  # 注册场景

    if not email or not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'error': '邮箱格式不正确'}), 400

    # 检查邮箱是否已被注册（排除当前用户自己的邮箱）
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        # 如果当前已登录，且邮箱属于当前用户，允许发送
        if current_user.is_authenticated and existing_user.id == current_user.id:
            pass  # 自己的邮箱，允许发送
        else:
            return jsonify({'success': False, 'error': '该邮箱已被注册'}), 400

    # 检查是否频繁发送（60秒内只能发一次）
    recent_code = EmailVerificationCode.query.filter_by(
        email=email, purpose=purpose, used=False
    ).order_by(EmailVerificationCode.created_at.desc()).first()

    if recent_code:
        elapsed = (datetime.utcnow() - recent_code.created_at).total_seconds()
        if elapsed < 60:
            return jsonify({
                'success': False,
                'error': f'请{int(60 - elapsed)}秒后再试'
            }), 429

    # 生成验证码
    code = EmailVerificationCode.generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # 保存验证码
    verification = EmailVerificationCode(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=expires_at
    )
    db.session.add(verification)
    db.session.commit()

    # 检查是否配置了邮箱
    mail_username = current_app.config.get('MAIL_USERNAME', '')
    if not mail_username:
        # 开发模式：直接返回验证码，方便测试
        current_app.logger.warning(f'邮箱未配置，开发模式验证码: {code}')
        return jsonify({
            'success': True,
            'message': '验证码已发送（开发模式）',
            'dev_code': code  # 开发模式下返回验证码方便测试
        })

    # 发送邮件
    if send_verification_code_email(email, code):
        return jsonify({'success': True, 'message': '验证码已发送到您的邮箱'})
    else:
        # 邮件发送失败，删除验证码记录
        db.session.delete(verification)
        db.session.commit()
        return jsonify({
            'success': False,
            'error': '邮件发送失败，请检查邮箱配置或稍后重试'
        }), 500


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))


# API: 获取当前用户信息
@auth_bp.route('/api/me')
@login_required
def api_me():
    return jsonify(current_user.to_dict())


# API: 获取用户列表（用于添加团队成员）
@auth_bp.route('/api/users')
@login_required
def api_users():
    search = request.args.get('q', '').strip()
    query = User.query.filter_by(role='user')
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.real_name.ilike(f'%{search}%'),
                User.student_id.ilike(f'%{search}%')
            )
        )
    users = query.limit(20).all()
    return jsonify([u.to_dict() for u in users])


# ==================== 个人信息与密码修改 ====================

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """个人信息页面 - 用户修改自己的信息（需要验证码）"""
    if request.method == 'POST':
        real_name = request.form.get('real_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        student_class = request.form.get('student_class', '').strip()
        verification_code = request.form.get('verification_code', '').strip()

        # 验证必填字段
        if not real_name or not student_id or not student_class:
            flash('真实姓名、学号、班级为必填项', 'danger')
            return redirect(url_for('auth.profile'))

        # 验证邮箱验证码
        if not verification_code:
            flash('请填写邮箱验证码', 'danger')
            return redirect(url_for('auth.profile'))

        code_record = EmailVerificationCode.query.filter_by(
            email=current_user.email,
            code=verification_code,
            used=False
        ).first()

        if not code_record:
            flash('验证码错误或已过期', 'danger')
            return redirect(url_for('auth.profile'))

        if code_record.is_expired():
            flash('验证码已过期，请重新获取', 'danger')
            return redirect(url_for('auth.profile'))

        # 标记验证码已使用
        code_record.used = True

        # 更新用户信息
        current_user.real_name = real_name
        current_user.student_id = student_id
        current_user.student_class = student_class
        db.session.commit()

        flash('个人信息更新成功', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html', user=current_user)


@auth_bp.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    """修改密码 - 用户自己修改（需要验证码）"""
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    verification_code = request.form.get('verification_code', '').strip()

    # 验证旧密码
    if not current_user.check_password(old_password):
        flash('旧密码错误', 'danger')
        return redirect(url_for('auth.profile'))

    # 验证新密码
    if len(new_password) < 6:
        flash('新密码长度不能少于6位', 'danger')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('auth.profile'))

    # 验证邮箱验证码
    if not verification_code:
        flash('请填写邮箱验证码', 'danger')
        return redirect(url_for('auth.profile'))

    code_record = EmailVerificationCode.query.filter_by(
        email=current_user.email,
        code=verification_code,
        used=False
    ).first()

    if not code_record:
        flash('验证码错误或已过期', 'danger')
        return redirect(url_for('auth.profile'))

    if datetime.utcnow() - code_record.created_at > timedelta(minutes=10):
        flash('验证码已过期，请重新获取', 'danger')
        return redirect(url_for('auth.profile'))

    # 标记验证码已使用
    code_record.used = True

    # 更新密码
    current_user.set_password(new_password)
    db.session.commit()

    flash('密码修改成功', 'success')
    return redirect(url_for('auth.profile'))


# ==================== 管理员修改用户信息 ====================

@auth_bp.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    """管理员编辑用户信息（不需要验证码）"""
    if not current_user.is_admin():
        flash('无权操作', 'danger')
        return redirect(url_for('project.dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'profile':
            # 修改个人信息
            real_name = request.form.get('real_name', '').strip()
            student_id = request.form.get('student_id', '').strip()
            student_class = request.form.get('student_class', '').strip()

            if not real_name or not student_id or not student_class:
                flash('真实姓名、学号、班级为必填项', 'danger')
                return redirect(url_for('auth.admin_edit_user', user_id=user_id))

            user.real_name = real_name
            user.student_id = student_id
            user.student_class = student_class
            db.session.commit()
            flash(f'用户 {user.username} 的信息已更新', 'success')

        elif action == 'password':
            # 修改密码
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if len(new_password) < 6:
                flash('新密码长度不能少于6位', 'danger')
                return redirect(url_for('auth.admin_edit_user', user_id=user_id))

            if new_password != confirm_password:
                flash('两次输入的新密码不一致', 'danger')
                return redirect(url_for('auth.admin_edit_user', user_id=user_id))

            user.set_password(new_password)
            db.session.commit()
            flash(f'用户 {user.username} 的密码已重置', 'success')

        return redirect(url_for('auth.admin_edit_user', user_id=user_id))

    return render_template('admin_edit_user.html', edit_user=user)
