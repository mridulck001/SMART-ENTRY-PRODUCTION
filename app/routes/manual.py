from flask import Blueprint, request, jsonify, render_template, current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db, limiter
from app.models import Visitor
from app.utils.validators import validate_name, validate_phone, validate_text, clean

manual_bp = Blueprint('manual', __name__, url_prefix='/api/v1/manual')


@manual_bp.route('/')
def visitor_dashboard():
    return render_template('visitor.html')


@manual_bp.route('/visitor', methods=['POST'])
@limiter.limit("60 per hour")
def add_visitor():
    """Manually log a walk-in visitor."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'JSON payload required.'}), 400

    errors = {}

    try:
        name = validate_name(data.get('name', ''))
    except ValueError as e:
        errors['name'] = str(e)

    try:
        phone = validate_phone(data.get('phone', ''))
    except ValueError as e:
        errors['phone'] = str(e)

    try:
        purpose = validate_text(data.get('purpose', ''), 255)
        if not purpose:
            raise ValueError("Purpose is required.")
    except ValueError as e:
        errors['purpose'] = str(e)

    if errors:
        return jsonify({'status': 'error', 'message': 'Validation failed.', 'errors': errors}), 422

    # Optional fields
    added_by  = clean(data.get('added_by', 'Gate Guard'), 100) if data.get('added_by') else 'Gate Guard'
    host_name = clean(data.get('host_name', ''), 100) if data.get('host_name') else None
    id_proof  = clean(data.get('id_proof', ''), 100)  if data.get('id_proof')  else None

    try:
        visitor = Visitor(
            name=name,
            purpose=purpose,
            phone=phone,
            added_by=added_by,
            host_name=host_name,
            id_proof=id_proof,
        )
        db.session.add(visitor)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("DB error adding visitor.")
        return jsonify({'status': 'error', 'message': 'Database error.'}), 500

    current_app.logger.info(
        f"Visitor logged: {visitor.name} | purpose={visitor.purpose} | by={visitor.added_by}"
    )

    return jsonify({
        'status': 'success',
        'message': 'Visitor entry recorded.',
        'data': {
            'visitor_id': visitor.id,
            'name': visitor.name,
            'entry_time': visitor.timestamp.isoformat(),
        },
    }), 201


@manual_bp.route('/visitor/<int:visitor_id>/exit', methods=['POST'])
@limiter.limit("60 per hour")
def log_visitor_exit(visitor_id: int):
    """Mark a visitor as exited."""
    from datetime import datetime, timezone
    visitor = Visitor.query.get(visitor_id)
    if not visitor:
        return jsonify({'status': 'error', 'message': 'Visitor not found.'}), 404
    if visitor.exit_time:
        return jsonify({'status': 'warning', 'message': 'Exit already recorded.'}), 200

    try:
        visitor.exit_time = datetime.now(timezone.utc)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Database error.'}), 500

    return jsonify({
        'status': 'success',
        'message': 'Visitor exit recorded.',
        'exit_time': visitor.exit_time.isoformat(),
    }), 200
