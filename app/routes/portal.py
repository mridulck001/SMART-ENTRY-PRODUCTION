from flask import Blueprint, request, jsonify, render_template, current_app
from sqlalchemy.exc import IntegrityError

from app import db, limiter
from app.models import User
from app.utils.qr_engine import QREngine
from app.utils.validators import (
    validate_name, validate_phone, validate_role, validate_text, clean
)

portal_bp = Blueprint('portal', __name__, url_prefix='/api/v1/portal')


@portal_bp.route('/')
def portal_home():
    return render_template('register.html')


@portal_bp.route('/register', methods=['POST'])
@limiter.limit("30 per hour")          # Prevent mass-registration abuse
def register_user():
    """Register a new user and return their QR access pass."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'JSON payload required.'}), 400

    # ── Validate & sanitize every field ────────────────────────
    errors = {}
    try:
        name = validate_name(data.get('name', ''))
    except ValueError as e:
        errors['name'] = str(e)

    try:
        role = validate_role(data.get('role', ''), User.VALID_ROLES)
    except ValueError as e:
        errors['role'] = str(e)

    try:
        department = validate_text(data.get('department', ''), 100)
        if not department:
            raise ValueError("Department is required.")
    except ValueError as e:
        errors['department'] = str(e)

    try:
        mobile_no = validate_phone(data.get('mobile_no', ''))
    except ValueError as e:
        errors['mobile_no'] = str(e)

    try:
        local_address = validate_text(data.get('local_address', ''), 500)
        if not local_address:
            raise ValueError("Address is required.")
    except ValueError as e:
        errors['local_address'] = str(e)

    default_transport = data.get('default_transport', 'Unknown')
    if default_transport not in User.VALID_TRANSPORT:
        default_transport = 'Unknown'

    if errors:
        return jsonify({
            'status': 'error',
            'message': 'Validation failed.',
            'errors': errors,
        }), 422

    # ── Persist ────────────────────────────────────────────────
    try:
        new_user = User(
            name=name,
            role=role,
            department=department,
            mobile_no=mobile_no,
            local_address=local_address,
            default_transport=default_transport,
        )
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error("Integrity error during user registration.")
        return jsonify({'status': 'error', 'message': 'Database constraint violation.'}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Unexpected DB error during registration.")
        return jsonify({'status': 'error', 'message': 'Internal server error.'}), 500

    # ── QR Code ────────────────────────────────────────────────
    qr_base64 = QREngine.generate_base64_qr(new_user.qr_uuid)
    if not qr_base64:
        # User was saved; just QR generation failed — still return success
        current_app.logger.error(f"QR generation failed for user {new_user.id}")
        return jsonify({
            'status': 'warning',
            'message': 'User registered but QR generation failed. Contact admin.',
            'data': {'user_id': new_user.id, 'name': new_user.name},
        }), 201

    current_app.logger.info(f"New user registered: {new_user.name} [{new_user.role}] (ID {new_user.id})")

    return jsonify({
        'status': 'success',
        'message': 'User registered successfully.',
        'data': {
            'user_id': new_user.id,
            'name': new_user.name,
            'role': new_user.role,
            'department': new_user.department,
            'qr_code_base64': qr_base64,
        },
    }), 201
