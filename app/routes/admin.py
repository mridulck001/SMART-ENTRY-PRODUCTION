from flask import Blueprint, Response, jsonify, request, session, current_app, render_template
from sqlalchemy import func, desc
from datetime import datetime, timezone, timedelta
import csv
import io

from app import db, limiter
from app.models import User, EntryLog, Visitor
from app.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')


# ── Authentication ─────────────────────────────────────────────

@admin_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def admin_login():
    """Simple password-based admin login, returns a session cookie."""
    data = request.get_json(silent=True)
    if not data or 'password' not in data:
        return jsonify({'status': 'error', 'message': 'Password required.'}), 400

    correct_password = current_app.config.get('ADMIN_PASSWORD', 'admin123')
    if data['password'] == correct_password:
        session.permanent = True
        session['is_admin'] = True
        return jsonify({'status': 'success', 'message': 'Logged in as admin.'}), 200

    current_app.logger.warning(f"Failed admin login from {request.remote_addr}")
    return jsonify({'status': 'error', 'message': 'Invalid password.'}), 401


@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return jsonify({'status': 'success', 'message': 'Logged out.'}), 200


# ── Dashboard stats ────────────────────────────────────────────

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    """Live summary stats for the admin dashboard."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users    = User.query.filter_by(is_active=True).count()
    entries_today  = EntryLog.query.filter(EntryLog.timestamp >= today_start, EntryLog.entry_type == 'IN').count()
    exits_today    = EntryLog.query.filter(EntryLog.timestamp >= today_start, EntryLog.entry_type == 'OUT').count()
    visitors_today = Visitor.query.filter(Visitor.timestamp >= today_start).count()

    # Recent 10 entries
    recent = (
        db.session.query(EntryLog, User)
        .join(User, EntryLog.user_id == User.id)
        .order_by(desc(EntryLog.timestamp))
        .limit(10)
        .all()
    )
    recent_list = [{
        'name': u.name,
        'role': u.role,
        'department': u.department,
        'entry_type': e.entry_type,
        'transport': e.transport_used,
        'time': e.timestamp.isoformat(),
    } for e, u in recent]

    return jsonify({
        'status': 'success',
        'data': {
            'total_registered_users': total_users,
            'entries_today': entries_today,
            'exits_today': exits_today,
            'on_premises': max(entries_today - exits_today, 0),
            'visitors_today': visitors_today,
            'recent_entries': recent_list,
        },
    }), 200


# ── User management ────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)
    search = request.args.get('q', '').strip()

    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.department.ilike(f'%{search}%')) |
            (User.role.ilike(f'%{search}%'))
        )

    paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'status': 'success',
        'data': [u.to_dict() for u in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages,
        },
    }), 200


@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id: int):
    """Revoke a user's access pass."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404
    user.is_active = False
    db.session.commit()
    current_app.logger.warning(f"User {user_id} ({user.name}) deactivated by admin.")
    return jsonify({'status': 'success', 'message': f'{user.name} deactivated.'}), 200


@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404
    user.is_active = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'{user.name} reactivated.'}), 200


# ── CSV Exports ────────────────────────────────────────────────

IST = timezone(timedelta(hours=5, minutes=30))

def _to_ist(dt: datetime) -> datetime:
    """Convert a datetime (naive=UTC or aware) to IST."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def _csv_response(rows: list, headers: list, filename: str) -> Response:
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerows(rows)
    return Response(
        si.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@admin_bp.route('/export/daily-register', methods=['GET'])
@admin_required
def export_daily_register():
    """Export entry log as CSV - defaults to today's data only."""
    date_filter = request.args.get('date')  # e.g. 2026-02-27
    
    # Default to today if no date specified
    if not date_filter:
        date_filter = datetime.now().strftime('%Y-%m-%d')
    
    try:
        target = datetime.strptime(date_filter, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        next_day = target + timedelta(days=1)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    
    query = db.session.query(EntryLog, User).join(User)\
        .filter(EntryLog.timestamp >= target, EntryLog.timestamp < next_day)\
        .order_by(desc(EntryLog.timestamp))

    logs = query.all()
    rows = [[
        log.id, user.name, user.role, user.department,
        log.entry_type,
        log.transport_used or user.default_transport or 'N/A',
        log.vehicle_number or '',
        log.scanned_by or '',
        _to_ist(log.timestamp).strftime('%d-%m-%Y %I:%M:%S %p IST'),
    ] for log, user in logs]

    return _csv_response(
        rows,
        ['Scan ID', 'Name', 'Role', 'Department', 'Type',
         'Transport', 'Vehicle No.', 'Scanned By', 'Time (IST)'],
        f'entry_register_{date_filter}.csv',
    )


@admin_bp.route('/export/visitors', methods=['GET'])
@admin_required
def export_visitors():
    """Export visitor log as CSV - defaults to today's data only."""
    date_filter = request.args.get('date')  # e.g. 2026-02-27
    
    # Default to today if no date specified
    if not date_filter:
        date_filter = datetime.now().strftime('%Y-%m-%d')
    
    try:
        target = datetime.strptime(date_filter, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        next_day = target + timedelta(days=1)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    
    visitors = Visitor.query\
        .filter(Visitor.timestamp >= target, Visitor.timestamp < next_day)\
        .order_by(desc(Visitor.timestamp)).all()
    
    rows = [[
        v.id, v.name, v.phone, v.purpose,
        v.host_name or '', v.id_proof or '',
        v.added_by or '',
        _to_ist(v.timestamp).strftime('%d-%m-%Y %I:%M:%S %p IST'),
        _to_ist(v.exit_time).strftime('%d-%m-%Y %I:%M:%S %p IST') if v.exit_time else 'Not Exited',
    ] for v in visitors]

    return _csv_response(
        rows,
        ['ID', 'Name', 'Phone', 'Purpose', 'Host', 'ID Proof',
         'Logged By', 'Entry Time (IST)', 'Exit Time (IST)'],
        f'visitor_log_{date_filter}.csv',
    )


@admin_bp.route('/dashboard-ui')
def dashboard_ui():
    return render_template('admin.html')
