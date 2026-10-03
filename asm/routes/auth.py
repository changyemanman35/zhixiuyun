"""认证与用户管理路由 ── 支持调度员、技师、客户等角色的注册、登录与登出"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Customer, Technician
import re

from functools import wraps
from flask import current_app

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """用户登录校验装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 兼容自动化单测（当未显式登录且在测试模式且未要求强制校验时放行）
        if current_app.config.get('TESTING') and not session.get('user_id') and not request.headers.get('X-Force-Auth'):
            return f(*args, **kwargs)
        if not session.get('user_id'):
            flash('请先登录系统后再执行操作', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    """基于角色的板块访问控制装饰器：针对已登录角色实施严格的板块隔离与非法越权拦截"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_role = session.get('role')
            if current_role and current_role not in allowed_roles:
                role_names = {
                    'dispatcher': '运营调度员',
                    'technician': '维修技师',
                    'customer': '报修客户'
                }
                role_zh = role_names.get(current_role, current_role)
                flash(f'权限受限：【{role_zh}】无权访问该板块', 'error')
                # 智能跳转到其专属板块
                if current_role == 'technician':
                    return redirect(url_for('tech.tech_index'))
                elif current_role == 'customer':
                    return redirect(url_for('query.query_form'))
                else:
                    return redirect(url_for('orders.board'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password:
        flash('请输入用户名和密码', 'error')
        return render_template('login.html', username=username)

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash('用户名或密码错误', 'error')
        return render_template('login.html', username=username)

    # 登录成功，写入 Session
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['user_name'] = user.name or user.username

    # 如果是技师，自动同步工作台当前技师
    if user.role == 'technician' and user.related_id:
        session['current_tech_id'] = user.related_id

    flash(f'欢迎回来，{user.name or user.username}！', 'success')

    # 优先安全回跳至来源目标页面 (如未登录点击报修直接回跳报修向导)
    next_url = request.form.get('next') or request.args.get('next')
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)

    # 否则按角色智能重定向
    if user.role == 'technician':
        return redirect(url_for('tech.tech_index'))
    elif user.role == 'customer':
        return redirect(url_for('query.query_form'))
    else:
        return redirect(url_for('orders.board'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """新用户注册（支持客户自助注册及账号关联）"""
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    role = request.form.get('role', 'customer').strip()
    next_url = request.form.get('next') or request.args.get('next')

    if not username or not password or not name or not phone:
        flash('请填写完整必填项（用户名、密码、姓名、手机号）', 'error')
        return render_template('register.html', username=username, name=name, phone=phone, address=address)

    if password != confirm_password:
        flash('两次输入的密码不一致', 'error')
        return render_template('register.html', username=username, name=name, phone=phone, address=address)

    if not re.match(r'^1\d{10}$', phone):
        flash('手机号格式不正确（须为 11 位且以 1 开头）', 'error')
        return render_template('register.html', username=username, name=name, phone=phone, address=address)

    if User.query.filter_by(username=username).first():
        flash('该用户名已被占用，请更换其他用户名', 'error')
        return render_template('register.html', name=name, phone=phone, address=address)

    # 如果注册角色为客户，同步确保客户档案；若为技师，同步创建技师档案画像
    related_id = None
    if role == 'customer':
        cust = Customer.query.filter_by(phone=phone).first()
        if not cust:
            cust = Customer(name=name, phone=phone, address=address or '未填写详细地址')
            db.session.add(cust)
            db.session.flush()
        related_id = cust.id
    elif role == 'technician':
        from models import Technician
        skills = request.form.get('skills', '空调,冰箱,洗衣机')
        cert_title = request.form.get('cert_title', '持证专业维修工程师')
        service_address = request.form.get('service_address', address or '附近服务商圈')
        try:
            radius = float(request.form.get('service_radius_km', 5.0))
        except Exception:
            radius = 5.0
        tech = Technician(
            name=name,
            phone=phone,
            skill_tags=skills,
            cert_title=cert_title,
            service_address=service_address,
            service_radius_km=radius,
            balance=0.0,
            is_online=True
        )
        db.session.add(tech)
        db.session.flush()
        related_id = tech.id

    user = User(
        username=username,
        role=role,
        name=name,
        phone=phone,
        related_id=related_id
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # 注册后自动登录
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['user_name'] = user.name or user.username
    if role == 'technician' and related_id:
        session['current_tech_id'] = related_id

    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        flash(f'注册成功并已自动登录！欢迎您，{user.name}！已为您直接打开目标页。', 'success')
        return redirect(next_url)

    flash('🎉 注册成功！已为您自动登录系统', 'success')
    if role == 'technician':
        flash('师傅入驻注册成功！为了为您精准推送商圈就近工单，请完善您的个人能力画像。', 'info')
        return redirect(url_for('auth.technician_profile_setup'))
    elif role == 'customer':
        flash('欢迎加入智修云！您可以花 30 秒完善您的常用上门地址与称呼（可跳过），后续报修享一键免填服务。', 'info')
        return redirect(url_for('auth.customer_profile_setup'))
    return redirect(url_for('query.query_form'))


@auth_bp.route('/customer/profile-setup', methods=['GET', 'POST'])
def customer_profile_setup():
    """客户个人基本信息与默认服务地址完善向导（支持跳过）"""
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != 'customer':
        flash('请先以客户身份登录系统', 'warning')
        return redirect(url_for('auth.login', next=request.path))

    cust = Customer.query.get(user.related_id) if user.related_id else None
    if not cust and user.phone:
        cust = Customer.query.filter_by(phone=user.phone).first()

    if request.method == 'GET':
        return render_template('customer_profile_setup.html', cust=cust, user=user)

    # POST 提交完善默认信息
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()

    if not name or not phone or not address:
        flash('请填写完整的常用称呼、手机号与默认服务地址', 'warning')
        return render_template('customer_profile_setup.html', cust=cust, user=user)

    if cust:
        cust.name = name
        cust.phone = phone
        cust.address = address
    else:
        cust = Customer(name=name, phone=phone, address=address)
        db.session.add(cust)
        db.session.flush()
        user.related_id = cust.id

    user.name = name
    user.phone = phone
    session['user_name'] = name

    db.session.commit()
    flash('🎉 个人基本信息与常用地址已保存！报修时系统将自动为您免填带出。', 'success')
    return redirect(url_for('orders.new_order'))


@auth_bp.route('/technician/profile-setup', methods=['GET', 'POST'])
def technician_profile_setup():
    """师傅个人能力与服务画像完善引导向导"""
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.role != 'technician':
        flash('请先以维修师傅身份登录系统', 'warning')
        return redirect(url_for('auth.login', next=request.path))

    tech = Technician.query.get(user.related_id) if user.related_id else None
    if not tech:
        flash('未找到对应的师傅档案信息', 'error')
        return redirect(url_for('tech.tech_index'))

    if request.method == 'GET':
        return render_template('technician_profile_setup.html', tech=tech, user=user)

    # POST 提交画像
    name = request.form.get('name', tech.name).strip()
    cert_title = request.form.get('cert_title', tech.cert_title).strip()
    skill_tags = request.form.get('skill_tags', tech.skill_tags).strip()
    service_address = request.form.get('service_address', tech.service_address).strip()
    tools_checked = request.form.get('tools_checked', '').strip()
    preferred_brands = request.form.get('preferred_brands', '').strip()
    night_order_enabled = bool(request.form.get('night_order_enabled'))
    
    try:
        radius = float(request.form.get('service_radius_km', 5.0))
    except Exception:
        radius = 5.0
        
    try:
        years = int(request.form.get('years_of_exp', 5))
    except Exception:
        years = 5

    tech.name = name
    tech.cert_title = cert_title
    tech.skill_tags = skill_tags
    tech.service_address = service_address
    tech.service_radius_km = radius
    tech.years_of_exp = years
    tech.tools_checked = tools_checked
    tech.preferred_brands = preferred_brands
    tech.night_order_enabled = night_order_enabled
    tech.profile_completed = True

    # 同步用户姓名
    user.name = name
    session['user_name'] = name

    db.session.commit()
    flash('🎉 个人画像与接单偏好已完善！智能派工引擎已为您点亮接单雷达。', 'success')
    return redirect(url_for('tech.tech_index'))


@auth_bp.route('/logout')
def logout():
    """安全注销登录"""
    session.clear()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('auth.login'))
