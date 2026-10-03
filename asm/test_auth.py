"""认证模块自动化单元测试 (test_auth.py) ── 覆盖用户注册、登录、Session状态、角色重定向与登出"""
import pytest
from app import create_app
from models import db, User, Customer


@pytest.fixture
def client():
    app = create_app(':memory:')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        # 创建默认测试用户
        admin = User(username='admin', role='dispatcher', name='系统调度员', phone='13800000001')
        admin.set_password('123456')
        tech = User(username='tech1', role='technician', name='张师傅', phone='13800000002')
        tech.set_password('123456')
        db.session.add_all([admin, tech])
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_login_page_renders(client):
    """测试登录页面正确渲染并包含快速填充演示账号按钮"""
    res = client.get('/login')
    assert res.status_code == 200
    assert '系统登录' in res.get_data(as_text=True)
    assert '填入调度员' in res.get_data(as_text=True)
    assert '填入技师' in res.get_data(as_text=True)


def test_login_success_dispatcher(client):
    """测试调度员登录成功并跳转到看板"""
    res = client.post('/login', data={'username': 'admin', 'password': '123456'}, follow_redirects=False)
    assert res.status_code == 302
    assert res.headers['Location'].endswith('/')


def test_login_success_technician(client):
    """测试技师登录成功并跳转到工作台"""
    res = client.post('/login', data={'username': 'tech1', 'password': '123456'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/tech' in res.headers['Location']


def test_login_wrong_password(client):
    """测试错误密码登录拒绝"""
    res = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert '用户名或密码错误' in res.get_data(as_text=True)


def test_register_page_renders(client):
    """测试注册页面渲染"""
    res = client.get('/register')
    assert res.status_code == 200
    assert '账号注册' in res.get_data(as_text=True)


def test_register_customer_and_login(client):
    """测试新客户自助注册、自动建档并可正常登录"""
    reg_data = {
        'username': 'newcust',
        'password': 'password123',
        'confirm_password': 'password123',
        'name': '新注册客户',
        'phone': '13912345678',
        'address': '深圳市高新科技园A座',
        'role': 'customer'
    }
    res = client.post('/register', data=reg_data, follow_redirects=True)
    assert res.status_code == 200
    assert '注册成功' in res.get_data(as_text=True)

    # 验证数据库是否创建了 User 和对应的 Customer
    with client.application.app_context():
        user = User.query.filter_by(username='newcust').first()
        assert user is not None
        assert user.check_password('password123')
        assert user.role == 'customer'
        assert user.related_id is not None
        cust = db.session.get(Customer, user.related_id)
        assert cust is not None
        assert cust.name == '新注册客户'
        assert cust.phone == '13912345678'

    # 使用新账号登录
    login_res = client.post('/login', data={'username': 'newcust', 'password': 'password123'}, follow_redirects=False)
    assert login_res.status_code == 302
    assert '/query' in login_res.headers['Location']


def test_register_password_mismatch(client):
    """测试两次密码不一致校验"""
    reg_data = {
        'username': 'mismatch_user',
        'password': 'password123',
        'confirm_password': 'different_password',
        'name': '测试',
        'phone': '13900000000',
        'role': 'customer'
    }
    res = client.post('/register', data=reg_data, follow_redirects=True)
    assert '两次输入的密码不一致' in res.get_data(as_text=True)


def test_logout(client):
    """测试安全退出登录"""
    # 先登录
    client.post('/login', data={'username': 'admin', 'password': '123456'})
    # 退出登录
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200
    assert '您已成功退出登录' in res.get_data(as_text=True)


def test_role_rbac_isolation(client):
    """测试三大角色的板块权限隔离与越权自动重定向"""
    # 1. 技师登录，尝试越权访问调度看板与字典维护
    client.post('/login', data={'username': 'tech1', 'password': '123456'})
    res_board = client.get('/', follow_redirects=False)
    assert res_board.status_code == 302
    assert '/tech' in res_board.headers['Location']

    res_parts = client.get('/parts', follow_redirects=False)
    assert res_parts.status_code == 302
    assert '/tech' in res_parts.headers['Location']
    client.get('/logout')

    # 2. 注册并登录客户账号，尝试越权访问技师工作台与管理报表
    client.post('/register', data={
        'username': 'cust_rbac', 'password': '123', 'confirm_password': '123',
        'name': '权限测试客户', 'phone': '13700000001', 'role': 'customer'
    })
    client.post('/login', data={'username': 'cust_rbac', 'password': '123'})
    
    res_tech = client.get('/tech', follow_redirects=False)
    assert res_tech.status_code == 302
    assert '/query' in res_tech.headers['Location']

    res_rep = client.get('/reports', follow_redirects=False)
    assert res_rep.status_code == 302
    assert '/query' in res_rep.headers['Location']
    client.get('/logout')

    # 3. 调度员登录，有权访问调度看板与字典管理
    client.post('/login', data={'username': 'admin', 'password': '123456'})
    res_admin_board = client.get('/')
    assert res_admin_board.status_code == 200
    res_admin_parts = client.get('/parts')
    assert res_admin_parts.status_code == 200
    client.get('/logout')


def test_role_navbar_content(client):
    """测试不同角色登录后导航菜单的动态差异化呈现"""
    # 1. 技师登录：能看到技师工作台，看不到管理报表与字典
    client.post('/login', data={'username': 'tech1', 'password': '123456'})
    res_tech = client.get('/tech')
    html_tech = res_tech.get_data(as_text=True)
    assert '技师工作台' in html_tech
    assert '管理报表' not in html_tech
    assert '字典与价目' not in html_tech
    client.get('/logout')

    # 2. 客户登录：能看到我的工单与自主报修，看不到调度看板与管理报表
    client.post('/register', data={
        'username': 'cust_rbac', 'password': '123', 'confirm_password': '123',
        'name': '权限测试客户', 'phone': '13700000001', 'role': 'customer'
    })
    client.post('/login', data={'username': 'cust_rbac', 'password': '123'})
    res_cust = client.get('/query')
    html_cust = res_cust.get_data(as_text=True)
    assert '我的工单与进度' in html_cust
    assert '在线自主报修' in html_cust
    assert '调度看板' not in html_cust
    assert '管理报表' not in html_cust
    client.get('/logout')


def test_portal_page_renders(client):
    """测试苹果与海尔风格官方售后服务大厅正常渲染"""
    res = client.get('/portal')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert '官方服务和维修' in html
    assert '费用是多少？' in html
    assert '维修申请' in html
    assert '延保与资产查询' in html

    # 别名 /home
    res_home = client.get('/home')
    assert res_home.status_code == 200


def test_portal_estimate_api(client):
    """测试 Apple Support 风格官方费用估算器接口"""
    # 1. 保内：费用全免
    res_in = client.post('/portal/api/estimate', json={'warranty_type': 'in'})
    assert res_in.status_code == 200
    data_in = res_in.get_json()
    assert data_in['total_fee'] == 0.0
    assert data_in['warranty'] is True

    # 2. 保外：上门费(50) + 工时费(80) = 130
    res_out = client.post('/portal/api/estimate', json={'warranty_type': 'out'})
    assert res_out.status_code == 200
    data_out = res_out.get_json()
    assert data_out['total_fee'] == 130.0
    assert data_out['warranty'] is False


def test_register_technician_and_profile_setup(client):
    """测试技师注册成功后精准重定向到个人画像引导向导，并成功完善画像档案"""
    reg_data = {
        'username': 'master_wang',
        'password': 'password888',
        'confirm_password': 'password888',
        'name': '王建国师傅',
        'phone': '13812349999',
        'address': '朝阳区大悦城服务站',
        'role': 'technician'
    }
    # 1. 注册提交
    res = client.post('/register', data=reg_data, follow_redirects=False)
    assert res.status_code == 302
    assert '/technician/profile-setup' in res.headers['Location']

    # 2. 访问画像向导页
    setup_res = client.get('/technician/profile-setup')
    assert setup_res.status_code == 200
    html = setup_res.get_data(as_text=True)
    assert '完善技师能力画像' in html
    assert '自备工具装备清单' in html

    # 3. 提交完善后的画像
    profile_data = {
        'name': '王建国师傅',
        'cert_title': '国家一级高级制冷与电气技师',
        'years_of_exp': '8',
        'skill_tags': '空调制冷与变频主板,冰箱冰柜压缩机与冷媒',
        'preferred_brands': '格力 GREE,海尔 Haier',
        'service_address': '北京市朝阳区高碑店服务网格',
        'service_radius_km': '15',
        'tools_checked': '数字万用表,双表阀充氟表,高空防坠安全自锁绳',
        'night_order_enabled': '1'
    }
    post_res = client.post('/technician/profile-setup', data=profile_data, follow_redirects=False)
    assert post_res.status_code == 302
    assert '/tech' in post_res.headers['Location']

    # 4. 验证数据库中技师画像已完备
    with client.application.app_context():
        from models import Technician
        tech = Technician.query.filter_by(phone='13812349999').first()
        assert tech is not None
        assert tech.cert_title == '国家一级高级制冷与电气技师'
        assert tech.years_of_exp == 8
        assert tech.service_radius_km == 15.0
        assert tech.profile_completed is True



if __name__ == '__main__':
    # 允许直接通过 python test_auth.py 运行
    import sys
    app = create_app(':memory:')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        admin = User(username='admin', role='dispatcher', name='系统调度员', phone='13800000001')
        admin.set_password('123456')
        tech = User(username='tech1', role='technician', name='张师傅', phone='13800000002')
        tech.set_password('123456')
        db.session.add_all([admin, tech])
        db.session.commit()
        c = app.test_client()

        test_login_page_renders(c)
        test_login_success_dispatcher(c)
        test_login_success_technician(c)
        test_login_wrong_password(c)
        test_register_page_renders(c)
        test_register_customer_and_login(c)
        test_register_password_mismatch(c)
        test_logout(c)
        test_role_rbac_isolation(c)
        test_role_navbar_content(c)
        test_portal_page_renders(c)
        test_portal_estimate_api(c)
        print("test_auth.py 全部 12 项断言通过！")
        sys.exit(0)

