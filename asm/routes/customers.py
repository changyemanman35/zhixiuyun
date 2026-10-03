from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Customer, Device, WorkOrder, User, utcnow
from rules import warranty_breakdown
from routes.auth import roles_required
import config
from datetime import datetime
import re

bp = Blueprint('customers', __name__)

@bp.route('/customers', methods=['GET'])
@roles_required('dispatcher', 'customer')
def index():
    current_role = session.get('role')
    user_id = session.get('user_id')
    
    # 若为客户角色，只允许查看该客户自己的设备资产（数据隔离）
    if current_role == 'customer' and user_id:
        user = User.query.get(user_id)
        if user and user.related_id:
            customers = Customer.query.filter_by(id=user.related_id).all()
        elif user and user.phone:
            customers = Customer.query.filter_by(phone=user.phone).all()
        else:
            customers = []
    else:
        customers = Customer.query.order_by(Customer.id.desc()).all()
        
    for c in customers:
        c.work_order_count = WorkOrder.query.filter_by(customer_id=c.id).count()
        for d in c.devices:
            d.warranty_info = warranty_breakdown(d)
    return render_template('customers.html', customers=customers, is_customer_view=(current_role == 'customer'))

@bp.route('/customers', methods=['POST'])
def create():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    company = request.form.get('company', '').strip()

    if not name or not phone or not address:
        flash('名称、手机号、地址为必填项', 'error')
        return redirect(url_for('customers.index'))

    if not re.match(r'^1\d{10}$', phone):
        flash('手机号格式不正确（11位数字，1开头）', 'error')
        return redirect(url_for('customers.index'))
        
    if Customer.query.filter_by(phone=phone).first():
        flash('手机号已存在', 'error')
        return redirect(url_for('customers.index'))
        
    c = Customer(name=name, phone=phone, address=address, company=company)
    db.session.add(c)
    db.session.commit()
    flash('客户创建成功', 'success')
    return redirect(url_for('customers.index'))

@bp.route('/customers/<int:cid>/edit', methods=['POST'])
def edit(cid):
    c = Customer.query.get_or_404(cid)
    old_phone = c.phone
    phone = request.form.get('phone', '').strip()
    c.name = request.form.get('name', '').strip() or c.name
    c.address = request.form.get('address', '').strip() or c.address
    c.company = request.form.get('company', '').strip()
    
    if phone and phone != old_phone:
        if not re.match(r'^1\d{10}$', phone):
            flash('手机号格式不正确', 'error')
            return redirect(url_for('customers.index'))
        if Customer.query.filter_by(phone=phone).first():
            flash('手机号已存在', 'error')
            return redirect(url_for('customers.index'))
        c.phone = phone
        flash('改手机号提示：历史工单需用新号码查询', 'info')
        
    db.session.commit()
    flash('客户修改成功', 'success')
    return redirect(url_for('customers.index'))

@bp.route('/customers/<int:cid>/delete', methods=['POST'])
def delete(cid):
    c = Customer.query.get_or_404(cid)
    device_count = c.devices.count()
    wo_count = WorkOrder.query.filter_by(customer_id=c.id).count()
    if device_count > 0 or wo_count > 0:
        flash(f'无法删除：包含 {device_count} 台设备，{wo_count} 个工单', 'error')
        return redirect(url_for('customers.index'))
        
    db.session.delete(c)
    db.session.commit()
    flash('客户已删除', 'success')
    return redirect(url_for('customers.index'))

@bp.route('/customers/<int:cid>/devices', methods=['POST'])
def add_device(cid):
    model = request.form.get('model', '').strip()
    purchase_date_str = request.form.get('purchase_date', '').strip()
    serial_no = request.form.get('serial_no', '').strip()
    warranty_months_str = request.form.get('warranty_months', '').strip()
    warranty_override_date_str = request.form.get('warranty_override_date', '').strip()
    
    if not model or not purchase_date_str:
        flash('型号和购买日期为必填项', 'error')
        return redirect(url_for('customers.index'))
        
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('购买日期格式不正确', 'error')
        return redirect(url_for('customers.index'))
        
    if purchase_date > utcnow().date():
        flash('购买日期不能晚于今天', 'error')
        return redirect(url_for('customers.index'))
        
    if serial_no and Device.query.filter_by(serial_no=serial_no).first():
        flash('序列号已存在', 'error')
        return redirect(url_for('customers.index'))
        
    try:
        warranty_months = int(warranty_months_str) if warranty_months_str else getattr(config, 'DEFAULT_WARRANTY_MONTHS', 12)
    except ValueError:
        warranty_months = getattr(config, 'DEFAULT_WARRANTY_MONTHS', 12)
        
    warranty_override_date = None
    if warranty_override_date_str:
        try:
            warranty_override_date = datetime.strptime(warranty_override_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    d = Device(
        customer_id=cid,
        model=model,
        serial_no=serial_no if serial_no else None,
        purchase_date=purchase_date,
        warranty_months=warranty_months,
        warranty_override_date=warranty_override_date
    )
    db.session.add(d)
    
    # 延保日期早于原截止时提示
    temp_info = warranty_breakdown(d)
    if warranty_override_date and temp_info['actual_end'] != warranty_override_date:
        flash('延保短于原截止，实际仍以原截止日为准', 'info')
        
    db.session.commit()
    flash('设备添加成功', 'success')
    return redirect(url_for('customers.index'))

@bp.route('/devices/<int:did>/edit', methods=['POST'])
def edit_device(did):
    d = Device.query.get_or_404(did)
    serial_no = request.form.get('serial_no', '').strip()
    if serial_no and serial_no != d.serial_no and Device.query.filter_by(serial_no=serial_no).first():
        flash('序列号已存在', 'error')
        return redirect(url_for('customers.index'))
        
    d.model = request.form.get('model', '').strip() or d.model
    if serial_no: d.serial_no = serial_no
    
    purchase_date_str = request.form.get('purchase_date', '').strip()
    if purchase_date_str:
        try:
            d.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    warranty_months_str = request.form.get('warranty_months', '').strip()
    if warranty_months_str:
        try:
            d.warranty_months = int(warranty_months_str)
        except ValueError:
            pass
            
    warranty_override_date_str = request.form.get('warranty_override_date', '').strip()
    if warranty_override_date_str:
        try:
            d.warranty_override_date = datetime.strptime(warranty_override_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    elif 'warranty_override_date' in request.form:
        d.warranty_override_date = None

    db.session.commit()
    flash('设备修改成功，修改档案不回溯已建工单的保修判定', 'success')
    return redirect(url_for('customers.index'))

@bp.route('/devices/<int:did>/delete', methods=['POST'])
def delete_device(did):
    d = Device.query.get_or_404(did)
    wo_count = WorkOrder.query.filter_by(device_id=d.id).count()
    if wo_count > 0:
        flash('无法删除：已产生工单', 'error')
        return redirect(url_for('customers.index'))
    db.session.delete(d)
    db.session.commit()
    flash('设备已删除', 'success')
    return redirect(url_for('customers.index'))
