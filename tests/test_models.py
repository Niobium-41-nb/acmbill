"""Tests for data models."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from models import (
    User, Project, TeamMember, ReimbursementItem,
    ProjectFile, EmailVerificationCode
)
from tests.conftest import login


class TestUserModel:
    """Test the User model."""

    def test_password_hashing(self, app):
        with app.app_context():
            user = User(username='pwtest', email='pw@test.com')
            user.set_password('secret123')
            assert user.password_hash is not None
            assert user.password_hash != 'secret123'

    def test_password_check_correct(self, normal_user):
        assert normal_user.check_password('user123') is True

    def test_password_check_wrong(self, normal_user):
        assert normal_user.check_password('wrongpass') is False

    def test_password_check_empty(self, normal_user):
        assert normal_user.check_password('') is False

    def test_is_admin_true(self, admin_user):
        assert admin_user.is_admin() is True
        assert admin_user.username == 'admin'

    def test_is_admin_false(self, normal_user):
        assert normal_user.is_admin() is False

    def test_user_default_role(self, app):
        with app.app_context():
            user = User(username='roletest', email='role@test.com')
            user.set_password('pass123')
            from models import db
            db.session.add(user)
            db.session.commit()
            assert user.role == 'user'

    def test_to_dict(self, normal_user):
        d = normal_user.to_dict()
        assert d['username'] == 'testuser'
        assert d['email'] == 'user@test.com'
        assert d['role'] == 'user'
        assert d['real_name'] == '测试用户'
        assert d['student_id'] == '2024001'
        assert 'id' in d

    def test_user_unique_username(self, app, normal_user):
        with app.app_context():
            from models import db
            duplicate = User(username='testuser', email='another@test.com')
            db.session.add(duplicate)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_user_unique_email(self, app, normal_user):
        with app.app_context():
            from models import db
            duplicate = User(username='another', email='user@test.com')
            db.session.add(duplicate)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_user_authenticated_property(self, normal_user):
        assert normal_user.is_authenticated is True

    def test_user_is_active(self, normal_user):
        assert normal_user.is_active is True

    def test_user_get_id(self, normal_user):
        assert normal_user.get_id() == str(normal_user.id)


class TestProjectModel:
    """Test the Project model."""

    def test_project_creation(self, app, normal_user):
        with app.app_context():
            from models import db
            p = Project(
                title='新项目',
                description='项目描述',
                competition_name='比赛A',
                competition_date='2026-06-01',
                owner_id=normal_user.id
            )
            db.session.add(p)
            db.session.commit()
            assert p.id is not None
            assert p.title == '新项目'
            assert p.status == 'draft'  # default
            assert p.owner_id == normal_user.id

    def test_to_dict(self, project):
        d = project.to_dict()
        assert d['title'] == '测试项目'
        assert d['status'] == 'draft'
        assert d['owner_name'] in ('测试用户', 'testuser')
        assert 'item_count' in d
        assert 'file_count' in d
        assert 'team_count' in d

    def test_project_requires_title(self, app, normal_user):
        with app.app_context():
            from models import db
            p = Project(owner_id=normal_user.id)
            db.session.add(p)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_project_requires_owner(self, app):
        with app.app_context():
            from models import db
            p = Project(title='无主项目')
            db.session.add(p)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


class TestReimbursementItemModel:
    """Test the ReimbursementItem model."""

    def test_item_creation(self, app, project):
        with app.app_context():
            from models import db
            item = ReimbursementItem(
                project_id=project.id,
                teacher='章英',
                reimbursement_date='2026-05-01',
                expense_category='报名费',
                content='报名费',
                amount=1000.00,
                applicant='张可凡',
                student_id='2024317220511',
                student_class='计算机类2405班'
            )
            db.session.add(item)
            db.session.commit()
            assert item.id is not None
            assert item.expense_category == '报名费'
            assert item.amount == 1000.00

    def test_to_dict_basic(self, item):
        d = item.to_dict()
        assert d['expense_category'] == '住宿费'
        assert d['amount'] == 1440.00
        assert d['applicant'] == '刘泽成'
        assert 'direction' not in d  # 非大交通费不包含

    def test_to_dict_transport(self, app, project):
        with app.app_context():
            from models import db
            item = ReimbursementItem(
                project_id=project.id,
                teacher='章英、李嘉位',
                reimbursement_date='2026-05-01',
                expense_category='大交通费',
                content='大交通费',
                direction='往',
                origin='武汉',
                destination='西安',
                transport_mode='机票',
                amount=1473.00,
                applicant='刘泽成',
                student_id='2024317240106',
                student_class='信科2401班'
            )
            db.session.add(item)
            db.session.commit()
            d = item.to_dict()
            assert d['expense_category'] == '大交通费'
            assert d['direction'] == '往'
            assert d['origin'] == '武汉'
            assert d['destination'] == '西安'
            assert d['transport_mode'] == '机票'

    def test_item_requires_required_fields(self, app, project):
        with app.app_context():
            from models import db
            item = ReimbursementItem(project_id=project.id)
            db.session.add(item)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()

    def test_default_expense_category(self, app, project):
        with app.app_context():
            from models import db
            item = ReimbursementItem(
                project_id=project.id,
                teacher='老师',
                reimbursement_date='2026-01-01',
                content='测试内容',
                amount=100.0,
                applicant='学生',
                student_id='123',
                student_class='班级'
            )
            db.session.add(item)
            db.session.commit()
            assert item.expense_category == '其他'


class TestTeamMemberModel:
    """Test the TeamMember model."""

    def test_team_member_creation(self, app, project, second_user):
        with app.app_context():
            from models import db
            tm = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm)
            db.session.commit()
            assert tm.id is not None

    def test_unique_constraint(self, app, project, second_user):
        with app.app_context():
            from models import db
            tm1 = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm1)
            db.session.commit()

            tm2 = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm2)
            import pytest
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


class TestEmailVerificationCode:
    """Test the EmailVerificationCode model."""

    def test_generate_code(self):
        code = EmailVerificationCode.generate_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_unique(self):
        codes = {EmailVerificationCode.generate_code() for _ in range(100)}
        # 6-digit codes have 10^6 possibilities, so at least a few unique ones
        assert len(codes) > 1

    def test_is_expired_false(self, app):
        with app.app_context():
            from models import db
            code = EmailVerificationCode(
                email='test@test.com',
                code='123456',
                purpose='register',
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            db.session.add(code)
            db.session.commit()
            assert code.is_expired() is False

    def test_is_expired_true(self, app):
        with app.app_context():
            from models import db
            code = EmailVerificationCode(
                email='test@test.com',
                code='123456',
                purpose='register',
                expires_at=datetime.utcnow() - timedelta(minutes=1)
            )
            db.session.add(code)
            db.session.commit()
            assert code.is_expired() is True


class TestProjectFileModel:
    """Test the ProjectFile model."""

    def test_file_creation(self, app, project, normal_user):
        with app.app_context():
            from models import db
            pf = ProjectFile(
                project_id=project.id,
                file_type='invoice',
                original_filename='发票.pdf',
                stored_filename='abc123.pdf',
                file_size=1024,
                uploaded_by=normal_user.id
            )
            db.session.add(pf)
            db.session.commit()
            assert pf.id is not None
            assert pf.file_type == 'invoice'

    def test_to_dict(self, app, project, normal_user):
        with app.app_context():
            from models import db
            pf = ProjectFile(
                project_id=project.id,
                file_type='payment',
                original_filename='支付截图.png',
                stored_filename='def456.png',
                file_size=2048,
                uploaded_by=normal_user.id
            )
            db.session.add(pf)
            db.session.commit()
            d = pf.to_dict()
            assert d['file_type'] == 'payment'
            assert d['original_filename'] == '支付截图.png'
            assert d['project_id'] == project.id
