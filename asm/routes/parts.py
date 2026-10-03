from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models import db, Part, FaultType, OrderPart, WorkOrder

bp = Blueprint('parts', __name__)

@bp.before_request
def check_permission():
    role = session.get('role')
    if role and role != 'dispatcher':
        role_zh = {'technician': '维修技师', 'customer': '报修客户'}.get(role, role)
        flash(f'权限受限：【{role_zh}】无权访问字典与价目维护板块', 'error')
        if role == 'technician':
            return redirect(url_for('tech.tech_index'))
        else:
            return redirect(url_for('query.query_form'))

@bp.route('/parts', methods=['GET'])
def index():
    parts = Part.query.order_by(Part.id.desc()).all()
    fault_types = FaultType.query.order_by(FaultType.id.desc()).all()
    
    for p in parts:
        p.used_count = OrderPart.query.filter_by(part_id=p.id).count()
        
    for f in fault_types:
        f.used_count = WorkOrder.query.filter_by(fault_type_id=f.id).count()
        
    return render_template('parts.html', parts=parts, fault_types=fault_types)

@bp.route('/parts', methods=['POST'])
def create_part():
    name = request.form.get('name', '').strip()
    unit_price_str = request.form.get('unit_price', '').strip()
    
    if not name or not unit_price_str:
        flash('名称和单价为必填项', 'error')
        return redirect(url_for('parts.index'))
        
    try:
        unit_price = float(unit_price_str)
        if unit_price < 0:
            raise ValueError
    except ValueError:
        flash('单价必须是有效的正数', 'error')
        return redirect(url_for('parts.index'))
        
    if Part.query.filter_by(name=name).first():
        flash('配件名称已存在', 'error')
        return redirect(url_for('parts.index'))
        
    p = Part(name=name, unit_price=unit_price)
    db.session.add(p)
    db.session.commit()
    flash('配件添加成功', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/parts/<int:pid>/edit', methods=['POST'])
def edit_part(pid):
    p = Part.query.get_or_404(pid)
    name = request.form.get('name', '').strip()
    unit_price_str = request.form.get('unit_price', '').strip()
    
    if name and name != p.name and Part.query.filter_by(name=name).first():
        flash('配件名称已存在', 'error')
        return redirect(url_for('parts.index'))
        
    if name:
        p.name = name
        
    if unit_price_str:
        try:
            unit_price = float(unit_price_str)
            if unit_price >= 0:
                p.unit_price = unit_price
        except ValueError:
            flash('单价不合法，未修改', 'error')
            
    used_count = OrderPart.query.filter_by(part_id=p.id).count()
    db.session.commit()
    flash(f'修改成功，改价不回溯历史工单（已用工单数：{used_count}，历史工单沿用快照价）', 'info')
    return redirect(url_for('parts.index'))

@bp.route('/parts/<int:pid>/delete', methods=['POST'])
def delete_part(pid):
    p = Part.query.get_or_404(pid)
    used_count = OrderPart.query.filter_by(part_id=p.id).count()
    if used_count > 0:
        flash('该配件已被工单引用，无法删除，建议改为停用状态', 'error')
        return redirect(url_for('parts.index'))
        
    db.session.delete(p)
    db.session.commit()
    flash('配件已删除', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/parts/<int:pid>/toggle', methods=['POST'])
def toggle_part(pid):
    p = Part.query.get_or_404(pid)
    p.active = not p.active
    db.session.commit()
    status = '启用' if p.active else '停用'
    flash(f'配件已{status}', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/fault-types', methods=['POST'])
def create_fault_type():
    name = request.form.get('name', '').strip()
    if not name:
        flash('名称为必填项', 'error')
        return redirect(url_for('parts.index'))
        
    if FaultType.query.filter_by(name=name).first():
        flash('故障类型名称已存在', 'error')
        return redirect(url_for('parts.index'))
        
    f = FaultType(name=name)
    db.session.add(f)
    db.session.commit()
    flash('故障类型添加成功', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/fault-types/<int:fid>/edit', methods=['POST'])
def edit_fault_type(fid):
    f = FaultType.query.get_or_404(fid)
    name = request.form.get('name', '').strip()
    
    if name and name != f.name and FaultType.query.filter_by(name=name).first():
        flash('故障类型名称已存在', 'error')
        return redirect(url_for('parts.index'))
        
    if name:
        f.name = name
    db.session.commit()
    flash('故障类型修改成功', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/fault-types/<int:fid>/delete', methods=['POST'])
def delete_fault_type(fid):
    f = FaultType.query.get_or_404(fid)
    used_count = WorkOrder.query.filter_by(fault_type_id=f.id).count()
    if used_count > 0:
        flash('该故障类型已被工单引用，无法删除', 'error')
        return redirect(url_for('parts.index'))
        
    db.session.delete(f)
    db.session.commit()
    flash('故障类型已删除', 'success')
    return redirect(url_for('parts.index'))

@bp.route('/fault-types/<int:fid>/toggle', methods=['POST'])
def toggle_fault_type(fid):
    f = FaultType.query.get_or_404(fid)
    f.active = not f.active
    db.session.commit()
    status = '启用' if f.active else '停用'
    flash(f'故障类型已{status}', 'success')
    return redirect(url_for('parts.index'))
