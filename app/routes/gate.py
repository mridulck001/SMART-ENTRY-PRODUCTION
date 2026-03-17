from flask import Blueprint, request, jsonify, render_template, current_app
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone, timedelta

from app import db, limiter
from app.models import User, EntryLog
from app.utils.validators import extract_uuid, clean

gate_bp = Blueprint('gate', __name__, url_prefix='/api/v1/gate')

# ── Constants ──────────────────────────────────────────────────
SCAN_COOLDOWN_SECONDS = 5   # Min seconds between two scans of the same pass


@gate_bp.route('/')
def gate_dashboard():
    return render_template('scanner.html')


@gate_bp.route('/scan', methods=['POST'])
@limiter.limit("120 per minute")       # ~2 scans/sec max per source IP
def process_scan():
    """
    Process a scanned QR code.
    Payload: { qr_uuid, transport_used?, vehicle_number?, entry_type?, scanned_by? }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'JSON payload required.'}), 400

    # ── UUID extraction & validation ───────────────────────────
    raw_uuid = data.get('qr_uuid', '')
    try:
        scanned_uuid = extract_uuid(raw_uuid)
    except ValueError:
        current_app.logger.warning(f"Invalid QR payload received: {str(raw_uuid)[:80]}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid QR code format.',
            'action': 'DENY',
        }), 400

    # ── Optional fields (sanitized) ────────────────────────────
    transport_used = data.get('transport_used') or None
    if transport_used:
        try:
            transport_used = clean(transport_used, 100)
        except ValueError:
            transport_used = None

    vehicle_number = data.get('vehicle_number') or None
    if vehicle_number:
        try:
            vehicle_number = clean(vehicle_number, 50).upper()
        except ValueError:
            vehicle_number = None

    entry_type = data.get('entry_type', 'IN').upper()
    if entry_type not in ('IN', 'OUT'):
        entry_type = 'IN'

    scanned_by = data.get('scanned_by') or 'Gate Terminal'

    # ── User lookup ────────────────────────────────────────────
    user = User.query.filter_by(qr_uuid=scanned_uuid, is_active=True).first()

    if not user:
        current_app.logger.warning(f"Scan attempt with unknown UUID: {scanned_uuid}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid or revoked entry pass.',
            'action': 'DENY',
        }), 404

    # ── Duplicate / rapid rescan guard ─────────────────────────
    cooldown_boundary = datetime.now(timezone.utc) - timedelta(seconds=SCAN_COOLDOWN_SECONDS)
    recent_entry = (
        EntryLog.query
        .filter(
            EntryLog.user_id == user.id,
            EntryLog.timestamp >= cooldown_boundary,
            EntryLog.entry_type == entry_type,
        )
        .first()
    )
    if recent_entry:
        current_app.logger.info(
            f"Duplicate scan blocked for user {user.id} within {SCAN_COOLDOWN_SECONDS}s"
        )
        return jsonify({
            'status': 'warning',
            'message': f'Entry already recorded in the last {SCAN_COOLDOWN_SECONDS} seconds.',
            'action': 'DUPLICATE',
            'data': {
                'name': user.name,
                'role': user.role,
                'entry_id': recent_entry.id,
            },
        }), 200

    # ── Log the entry ──────────────────────────────────────────
    try:
        new_entry = EntryLog(
            user_id=user.id,
            transport_used=transport_used or user.default_transport,
            vehicle_number=vehicle_number,
            entry_type=entry_type,
            scanned_by=scanned_by,
        )
        db.session.add(new_entry)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("DB error while logging entry.")
        return jsonify({'status': 'error', 'message': 'Database error. Please retry.'}), 500

    ts = new_entry.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    entry_time_iso = ts.astimezone(timezone.utc).isoformat()
    current_app.logger.info(
        f"Entry [{entry_type}] logged: {user.name} ({user.role}) at {entry_time_iso}"
    )

    return jsonify({
        'status': 'success',
        'message': 'Entry approved.',
        'action': 'ALLOW',
        'data': {
            'name': user.name,
            'role': user.role,
            'department': user.department,
            'entry_time': entry_time_iso,
            'transport_used': new_entry.transport_used,
            'entry_type': entry_type,
            'entry_id': new_entry.id,
        },
    }), 200


@gate_bp.route('/update-transport/<int:entry_id>', methods=['POST'])
@limiter.limit("30 per minute")
def update_transport(entry_id: int):
    """Update transport details for a recent entry log."""
    data = request.get_json(silent=True)
    if not data or 'transport_used' not in data:
        return jsonify({'status': 'error', 'message': 'transport_used is required.'}), 400

    try:
        transport_used = clean(data['transport_used'], 100)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 422

    vehicle_number = data.get('vehicle_number') or None
    if vehicle_number:
        try:
            vehicle_number = clean(vehicle_number, 50).upper()
        except ValueError:
            vehicle_number = None

    entry = EntryLog.query.get(entry_id)
    if not entry:
        return jsonify({'status': 'error', 'message': 'Entry log not found.'}), 404

    # Normalise timestamp to UTC-aware before comparison
    entry_ts = entry.timestamp
    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.replace(tzinfo=timezone.utc)

    # Only allow updates within 15 minutes of the original scan
    age = (datetime.now(timezone.utc) - entry_ts).total_seconds()
    if age > 900:
        return jsonify({'status': 'error', 'message': 'Update window expired (15 min).'}), 403

    try:
        entry.transport_used = transport_used
        entry.vehicle_number = vehicle_number
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error.'}), 500

    current_app.logger.info(f"Transport updated for entry {entry_id}: {transport_used}")
    return jsonify({'status': 'success', 'message': 'Transport updated.'}), 200


@gate_bp.route('/today-stats', methods=['GET'])
def today_stats():
    """Returns entry/exit counts for today. Used by dashboard widgets."""
    from sqlalchemy import func
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        in_count = EntryLog.query.filter(
            EntryLog.timestamp >= today_start,
            EntryLog.entry_type == 'IN',
        ).count()
        out_count = EntryLog.query.filter(
            EntryLog.timestamp >= today_start,
            EntryLog.entry_type == 'OUT',
        ).count()
        on_premises = in_count - out_count
        return jsonify({
            'status': 'success',
            'data': {
                'entries_today': in_count,
                'exits_today': out_count,
                'currently_on_premises': max(on_premises, 0),
            },
        }), 200
    except Exception:
        current_app.logger.exception("Error fetching today stats.")
        return jsonify({'status': 'error', 'message': 'Could not fetch stats.'}), 500
