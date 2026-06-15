from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    email_verified = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')  # 'admin' or 'user'
    student_id = db.Column(db.String(32), nullable=True)
    student_class = db.Column(db.String(64), nullable=True)
    real_name = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 用户创建的项目
    owned_projects = db.relationship('Project', foreign_keys='Project.owner_id',
                                     backref='owner', lazy='dynamic')
    # 用户参与的项目（组队）
    team_members = db.relationship('TeamMember', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'email_verified': self.email_verified,
            'role': self.role,
            'real_name': self.real_name,
            'student_id': self.student_id,
            'student_class': self.student_class,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }


class EmailVerificationCode(db.Model):
    """邮箱验证码"""
    __tablename__ = 'email_verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default='register')  # 'register' or 'reset'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    @staticmethod
    def generate_code():
        """生成6位数字验证码"""
        return ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    competition_name = db.Column(db.String(200), nullable=True)
    competition_date = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft, submitted, approved, rejected
    reimburse_status = db.Column(db.String(20), default='draft')  # draft, cannot_insure, reimbursed
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 报销条目
    reimbursement_items = db.relationship('ReimbursementItem', backref='project',
                                          lazy='dynamic', cascade='all, delete-orphan')
    # 上传的文件
    files = db.relationship('ProjectFile', backref='project',
                            lazy='dynamic', cascade='all, delete-orphan')
    # 团队成员
    team_members = db.relationship('TeamMember', backref='project',
                                   lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'competition_name': self.competition_name,
            'competition_date': self.competition_date,
            'status': self.status,
            'reimburse_status': self.reimburse_status,
            'owner_id': self.owner_id,
            'owner_name': self.owner.real_name or self.owner.username,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else '',
            'item_count': self.reimbursement_items.count(),
            'file_count': self.files.count(),
            'team_count': self.team_members.count()
        }


class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_team_member'),)


class ReimbursementItem(db.Model):
    """备案表条目"""
    __tablename__ = 'reimbursement_items'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)

    # 备案表字段
    teacher = db.Column(db.String(100), nullable=False)  # 指导老师
    reimbursement_date = db.Column(db.String(20), nullable=False)  # 报账时间
    expense_category = db.Column(db.String(20), nullable=False, default='其他')  # 费用类别: 报名费/住宿费/大交通费/小交通
    content = db.Column(db.String(200), nullable=False)  # 报账内容（具体说明）
    # 大交通费专属字段
    direction = db.Column(db.String(10), nullable=True)  # 往/返
    origin = db.Column(db.String(100), nullable=True)  # 起点
    destination = db.Column(db.String(100), nullable=True)  # 终点
    transport_mode = db.Column(db.String(20), nullable=True)  # 机票/车票
    amount = db.Column(db.Float, nullable=False)  # 支出金额
    applicant = db.Column(db.String(64), nullable=False)  # 报账人
    student_id = db.Column(db.String(32), nullable=False)  # 学号
    student_class = db.Column(db.String(64), nullable=False)  # 班级

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联的文件
    files = db.relationship('ProjectFile', backref='reimbursement_item',
                            foreign_keys='ProjectFile.item_id',
                            lazy='dynamic')

    def to_dict(self):
        d = {
            'id': self.id,
            'project_id': self.project_id,
            'teacher': self.teacher,
            'reimbursement_date': self.reimbursement_date,
            'expense_category': self.expense_category,
            'content': self.content,
            'amount': self.amount,
            'applicant': self.applicant,
            'student_id': self.student_id,
            'student_class': self.student_class,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }
        if self.expense_category == '大交通费':
            d['direction'] = self.direction
            d['origin'] = self.origin
            d['destination'] = self.destination
            d['transport_mode'] = self.transport_mode
        return d


class ProjectFile(db.Model):
    """项目文件（发票、支付记录、辅助材料）"""
    __tablename__ = 'project_files'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('reimbursement_items.id'), nullable=True)  # 关联的条目ID
    file_type = db.Column(db.String(20), nullable=False)  # 'invoice', 'payment', 'support'
    original_filename = db.Column(db.String(256), nullable=False)
    stored_filename = db.Column(db.String(256), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'item_id': self.item_id,
            'file_type': self.file_type,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'uploaded_by': self.uploaded_by,
            'uploader_name': self.uploader.real_name or self.uploader.username if self.uploader else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }
