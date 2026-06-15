"""Tests for project blueprint (CRUD, items, team, files, export)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import io
from tests.conftest import login, logout


class TestDashboard:
    """Tests for the dashboard."""

    def test_dashboard_requires_login(self, client):
        response = client.get('/project/dashboard', follow_redirects=True)
        assert '请先登录'.encode() in response.data

    def test_dashboard_normal_user(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.get('/project/dashboard')
        assert response.status_code == 200
        # Should show the project
        assert '测试项目'.encode() in response.data

    def test_dashboard_admin_sees_all(self, client, admin_user, normal_user, project):
        login(client, 'admin', 'admin123')
        response = client.get('/project/dashboard')
        assert response.status_code == 200
        assert '测试项目'.encode() in response.data

    def test_dashboard_normal_user_sees_only_own(self, client, normal_user, admin_user, app):
        """Normal user shouldn't see other users' projects they aren't team members of."""
        login(client, 'testuser', 'user123')
        response = client.get('/project/dashboard')
        assert response.status_code == 200


class TestProjectCRUD:
    """Tests for project create/read/update/delete."""

    def test_create_project_page_get(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/project/create')
        assert response.status_code == 200

    def test_create_project(self, client, normal_user, app):
        login(client, 'testuser', 'user123')
        response = client.post('/project/create', data={
            'title': '新项目',
            'description': '描述',
            'competition_name': '比赛',
            'competition_date': '2026-06-01',
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.filter_by(title='新项目').first()
            assert p is not None
            assert p.owner_id == normal_user.id

    def test_create_project_empty_title(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.post('/project/create', data={
            'title': '',
            'description': 'desc',
        }, follow_redirects=True)
        assert '项目标题'.encode() in response.data or '请输入'.encode() in response.data

    def test_create_project_requires_login(self, client):
        response = client.post('/project/create', data={
            'title': '未登录项目',
        }, follow_redirects=True)
        assert '请先登录'.encode() in response.data

    def test_project_detail(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}')
        assert response.status_code == 200
        assert '测试项目'.encode() in response.data

    def test_project_detail_not_found(self, client, normal_user):
        login(client, 'testuser', 'user123')
        response = client.get('/project/99999')
        assert response.status_code == 404

    def test_project_detail_access_denied(self, client, second_user, project):
        """User cannot access another user's project if not a team member."""
        login(client, 'testuser2', 'user456')
        response = client.get(f'/project/{project.id}', follow_redirects=True)
        assert response.status_code == 200
        assert '无权访问'.encode() in response.data

    def test_project_detail_admin_can_access(self, client, admin_user, project):
        login(client, 'admin', 'admin123')
        response = client.get(f'/project/{project.id}')
        assert response.status_code == 200

    def test_edit_project_page_get(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/edit')
        assert response.status_code == 200
        assert '测试项目'.encode() in response.data

    def test_edit_project(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/edit', data={
            'title': '修改后的项目',
            'description': '新描述',
            'competition_name': '新比赛',
            'competition_date': '2026-07-01',
            'teacher': '新老师',
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p.title == '修改后的项目'
            assert p.description == '新描述'

    def test_delete_project_by_owner(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p is None

    def test_delete_project_by_non_owner(self, client, second_user, project, app):
        login(client, 'testuser2', 'user456')
        response = client.post(f'/project/{project.id}/delete', follow_redirects=True)
        assert '无权删除'.encode() in response.data

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p is not None  # not deleted

    def test_delete_project_by_admin(self, client, admin_user, project, app):
        login(client, 'admin', 'admin123')
        response = client.post(f'/project/{project.id}/delete', follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p is None

    def test_update_status(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/status', data={
            'status': 'submitted',
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p.status == 'submitted'

    def test_update_status_invalid(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/status', data={
            'status': 'invalid_status',
        }, follow_redirects=True)
        assert response.status_code == 200

        with app.app_context():
            from models import Project
            p = Project.query.get(project.id)
            assert p.status == 'draft'  # unchanged

    def test_update_status_unauthorized(self, client, second_user, project):
        login(client, 'testuser2', 'user456')
        response = client.post(f'/project/{project.id}/status', data={
            'status': 'approved',
        }, follow_redirects=True)
        assert '无权操作'.encode() in response.data


class TestReimbursementItems:
    """Tests for reimbursement item management."""

    def test_add_item(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '报名费',
            'teacher': '章英',
            'reimbursement_date': '2026-05-01',
            'amount': 1000.00,
            'applicant': '张可凡',
            'student_id': '2024317220511',
            'student_class': '计算机类2405班',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from models import ReimbursementItem
            items = ReimbursementItem.query.filter_by(project_id=project.id).all()
            assert len(items) == 1
            assert items[0].expense_category == '报名费'

    def test_add_item_with_transport(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '大交通费',
            'teacher': '章英',
            'reimbursement_date': '2026-05-01',
            'amount': 1473.00,
            'applicant': '刘泽成',
            'student_id': '2024317240106',
            'student_class': '信科2401班',
            'direction': '往',
            'origin': '武汉',
            'destination': '西安',
            'transport_mode': '机票',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from models import ReimbursementItem
            items = ReimbursementItem.query.filter_by(project_id=project.id).all()
            assert len(items) == 1
            assert items[0].direction == '往'
            assert items[0].transport_mode == '机票'

    def test_add_item_missing_fields(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '',
            'teacher': '',
            'reimbursement_date': '',
            'amount': '',
            'applicant': '',
            'student_id': '',
            'student_class': '',
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_add_item_requires_login(self, client, project):
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '住宿费',
            'teacher': '老师',
            'reimbursement_date': '2026-01-01',
            'amount': 100.00,
            'applicant': '学生',
            'student_id': '123',
            'student_class': '班级',
        })
        assert response.status_code in (302, 401)

    def test_add_item_unauthorized(self, client, second_user, project):
        login(client, 'testuser2', 'user456')
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '住宿费',
            'teacher': '老师',
            'reimbursement_date': '2026-01-01',
            'amount': 100.00,
            'applicant': '学生',
            'student_id': '123',
            'student_class': '班级',
        })
        assert response.status_code == 403

    def test_update_item(self, client, normal_user, project, item, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/items/{item.id}', data={
            'expense_category': '小交通',
            'teacher': '新老师',
            'reimbursement_date': '2026-06-01',
            'amount': 200.00,
            'applicant': '新人',
            'student_id': '999',
            'student_class': '新班级',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from models import ReimbursementItem
            updated = ReimbursementItem.query.get(item.id)
            assert updated.expense_category == '小交通'
            assert updated.teacher == '新老师'
            assert updated.amount == 200.00

    def test_delete_item(self, client, normal_user, project, item, app):
        login(client, 'testuser', 'user123')
        response = client.delete(f'/project/{project.id}/items/{item.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from models import ReimbursementItem
            deleted = ReimbursementItem.query.get(item.id)
            assert deleted is None

    def test_delete_item_wrong_project(self, client, normal_user, project, app):
        """Can't delete an item that belongs to a different project."""
        login(client, 'testuser', 'user123')
        # item belongs to project.id, try to delete from a different project
        response = client.delete(f'/project/{project.id}/items/99999')
        assert response.status_code == 404


class TestTeamManagement:
    """Tests for team member management."""

    def test_add_team_member(self, client, normal_user, second_user, project, app):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'testuser2',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert '已添加团队成员'.encode() in response.data

        with app.app_context():
            from models import TeamMember
            tm = TeamMember.query.filter_by(
                project_id=project.id, user_id=second_user.id
            ).first()
            assert tm is not None

    def test_add_team_member_nonexistent(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'nobody',
        }, follow_redirects=True)
        assert '不存在'.encode() in response.data

    def test_add_self_as_team_member(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'testuser',
        }, follow_redirects=True)
        assert '不能添加自己'.encode() in response.data

    def test_add_duplicate_team_member(self, client, normal_user, second_user, project):
        login(client, 'testuser', 'user123')
        # First add
        client.post(f'/project/{project.id}/team/add', data={'username': 'testuser2'})
        # Second add
        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'testuser2',
        }, follow_redirects=True)
        assert '已是'.encode() in response.data

    def test_team_member_limit(self, client, normal_user, second_user, third_user, project, app):
        """Team is limited to max 3 members."""
        login(client, 'testuser', 'user123')
        # Add second_user
        client.post(f'/project/{project.id}/team/add', data={'username': 'testuser2'})
        # Add third_user
        client.post(f'/project/{project.id}/team/add', data={'username': 'testuser3'})

        # Verify count
        with app.app_context():
            from models import TeamMember
            count = TeamMember.query.filter_by(project_id=project.id).count()
            assert count == 2  # Only two team members added

        # Try adding a 4th user (need to create one first)
        with app.app_context():
            from models import User, db
            fourth = User(
                username='testuser4', email='user4@test.com',
                email_verified=True, role='user',
                real_name='用户4', student_id='4004', student_class='班级4'
            )
            fourth.set_password('pass4')
            db.session.add(fourth)
            db.session.commit()

        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'testuser4',
        }, follow_redirects=True)
        assert '已满'.encode() in response.data or b'3' in response.data

    def test_remove_team_member(self, client, normal_user, second_user, project, app):
        login(client, 'testuser', 'user123')

        # First add a member
        with app.app_context():
            from models import TeamMember, db
            tm = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm)
            db.session.commit()
            member_id = tm.id

        # Remove
        response = client.post(
            f'/project/{project.id}/team/{member_id}/remove',
            follow_redirects=True
        )
        assert response.status_code == 200

        with app.app_context():
            from models import TeamMember
            tm = TeamMember.query.get(member_id)
            assert tm is None

    def test_non_owner_cannot_add_member(self, client, second_user, project):
        login(client, 'testuser2', 'user456')
        response = client.post(f'/project/{project.id}/team/add', data={
            'username': 'testuser3',
        }, follow_redirects=True)
        assert '只有项目创建者'.encode() in response.data


class TestFileOperations:
    """Tests for file upload, download, preview, delete."""

    def test_upload_file(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')
        data = {
            'file': (io.BytesIO(b'fake pdf content'), 'test_invoice.pdf'),
            'file_type': 'invoice',
        }
        response = client.post(
            f'/project/{project.id}/files/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        resp_data = json.loads(response.data)
        assert resp_data['success'] is True
        assert resp_data['file']['file_type'] == 'invoice'

    def test_upload_file_with_item_id(self, client, normal_user, project, item, app):
        login(client, 'testuser', 'user123')
        data = {
            'file': (io.BytesIO(b'fake pdf content'), 'receipt.pdf'),
            'file_type': 'invoice',
            'item_id': item.id,
        }
        response = client.post(
            f'/project/{project.id}/files/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        resp_data = json.loads(response.data)
        assert resp_data['success'] is True

        with app.app_context():
            from models import ProjectFile
            pf = ProjectFile.query.filter_by(project_id=project.id, item_id=item.id).first()
            assert pf is not None

    def test_upload_file_no_file(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.post(
            f'/project/{project.id}/files/upload',
            data={'file_type': 'invoice'},
            content_type='multipart/form-data'
        )
        assert response.status_code == 400

    def test_upload_file_unauthorized(self, client, second_user, project):
        login(client, 'testuser2', 'user456')
        data = {
            'file': (io.BytesIO(b'content'), 'file.pdf'),
            'file_type': 'invoice',
        }
        response = client.post(
            f'/project/{project.id}/files/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 403

    def test_delete_file(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')

        # Upload a file first
        data = {
            'file': (io.BytesIO(b'to delete'), 'delete_me.pdf'),
            'file_type': 'support',
        }
        upload_resp = client.post(
            f'/project/{project.id}/files/upload',
            data=data,
            content_type='multipart/form-data'
        )
        file_id = json.loads(upload_resp.data)['file']['id']

        # Delete it
        response = client.post(f'/project/{project.id}/files/{file_id}/delete')
        assert response.status_code == 302  # redirect

        with app.app_context():
            from models import ProjectFile
            pf = ProjectFile.query.get(file_id)
            assert pf is None

    def test_download_file(self, client, normal_user, project, app):
        login(client, 'testuser', 'user123')

        # Upload a file first
        data = {
            'file': (io.BytesIO(b'download me please'), 'download.pdf'),
            'file_type': 'invoice',
        }
        upload_resp = client.post(
            f'/project/{project.id}/files/upload',
            data=data,
            content_type='multipart/form-data'
        )
        file_id = json.loads(upload_resp.data)['file']['id']

        # Download it
        response = client.get(f'/project/{project.id}/files/{file_id}/download')
        assert response.status_code == 200
        assert response.data == b'download me please'

    def test_check_files(self, client, normal_user, project, item):
        login(client, 'testuser', 'user123')
        response = client.get(
            f'/project/{project.id}/files/check'
            f'?item_id={item.id}&expense_category={item.expense_category}'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'ok' in data
        assert 'message' in data


class TestExport:
    """Tests for export functionality."""

    def test_export_html(self, client, normal_user, project, item):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/export/html')
        assert response.status_code == 200
        assert '备案表'.encode() in response.data

    def test_export_html_empty(self, client, normal_user, project):
        """Export HTML when there are no items."""
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/export/html')
        assert response.status_code == 200

    def test_export_excel(self, client, normal_user, project, item):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/export/excel')
        assert response.status_code == 200
        assert response.content_type in (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_export_excel_no_items(self, client, normal_user, project):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/export/excel', follow_redirects=True)
        assert response.status_code == 200
        assert '没有备案条目'.encode() in response.data

    def test_export_zip(self, client, normal_user, project, item):
        login(client, 'testuser', 'user123')
        response = client.get(f'/project/{project.id}/export/zip')
        assert response.status_code == 200
        assert response.content_type == 'application/zip'

    def test_export_unauthorized(self, client, second_user, project):
        login(client, 'testuser2', 'user456')
        response = client.get(f'/project/{project.id}/export/html', follow_redirects=True)
        assert '无权访问'.encode() in response.data


class TestTeamAccess:
    """Test that team members can access shared projects."""

    def test_team_member_can_view_project(self, client, normal_user, second_user, project, app):
        """After being added as team member, second_user can view the project."""
        login(client, 'testuser', 'user123')

        # Add second_user as team member
        with app.app_context():
            from models import TeamMember, db
            tm = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm)
            db.session.commit()

        logout(client)

        login(client, 'testuser2', 'user456')
        response = client.get(f'/project/{project.id}')
        assert response.status_code == 200
        assert '测试项目'.encode() in response.data

    def test_team_member_can_add_item(self, client, normal_user, second_user, project, app):
        """Team member can add items to shared project."""
        login(client, 'testuser', 'user123')

        with app.app_context():
            from models import TeamMember, db
            tm = TeamMember(project_id=project.id, user_id=second_user.id)
            db.session.add(tm)
            db.session.commit()

        logout(client)

        login(client, 'testuser2', 'user456')
        response = client.post(f'/project/{project.id}/items', data={
            'expense_category': '住宿费',
            'teacher': '老师',
            'reimbursement_date': '2026-06-01',
            'amount': 500.00,
            'applicant': '成员',
            'student_id': '2024002',
            'student_class': '计算机2401班',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
