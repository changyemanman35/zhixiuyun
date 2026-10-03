"""ASM 应用入口 ── Flask 应用工厂与 Blueprint 注册"""
import os
from flask import Flask, redirect, url_for
from models import db
import config


def create_app(db_path=None):
    """应用工厂"""
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # 配置
    actual_db = db_path or config.DATABASE_PATH
    if actual_db.startswith('sqlite:///'):
        actual_db = actual_db[10:]
    if actual_db != ':memory:':
        db_dir = os.path.dirname(actual_db)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{actual_db}'
    if actual_db != ':memory:':
        db_dir = os.path.dirname(actual_db)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{actual_db}'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = config.SECRET_KEY

    # 初始化 ORM
    db.init_app(app)

    # 注入模板全局变量
    import rules
    from flask import session
    @app.context_processor
    def inject_globals():
        current_user = None
        if session.get('user_id'):
            current_user = {
                'id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('role'),
                'name': session.get('user_name', session.get('username')),
                'is_authenticated': True
            }
        role_labels = {
            'dispatcher': '调度员',
            'technician': '维修技师',
            'customer': '报修客户'
        }
        return {
            'config': config,
            'rules': rules,
            'current_user': current_user,
            'ROLE_LABELS': role_labels,
            'STATUS_LABELS': config.STATUS_LABELS,
            'STATUS_COLORS': config.STATUS_COLORS,
        }

    # 注册 Blueprint
    from routes.orders import orders_bp
    from routes.customers import bp as customers_bp
    from routes.parts import bp as parts_bp
    from routes.reports import bp as reports_bp
    from routes.query import query_bp
    from routes.demo import bp as demo_bp
    from routes.tech import bp as tech_bp
    from routes.auth import auth_bp
    from routes.portal import portal_bp
    from routes.copilot import copilot_bp

    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(parts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(tech_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(copilot_bp)

    # 健康检查
    @app.route('/health')
    def health():
        import json
        return json.dumps({'status': 'ok', 'statuses': config.STATUSES}), 200, {'Content-Type': 'application/json'}

    @app.route('/PPMondwest-Regular.woff2')
    def ppmondwest_font():
        return '', 204

    # 首次运行自动建表与字段平滑迁移（NFR-2 / 企业级演进）
    from models import init_db
    init_db(app)

    return app


app = create_app()

if __name__ == '__main__':
    print('=' * 60)
    print('  售后服务管理系统 (ASM) v1')
    print('  http://127.0.0.1:5000')
    print('=' * 60)
    # 检查是否有数据
    with app.app_context():
        from models import WorkOrder
        count = WorkOrder.query.count()
        if count == 0:
            print('  ⚠ 数据库为空，请运行 python seed.py --reset 生成演示数据')
    print('=' * 60)
    app.run(debug=True, port=5000)
