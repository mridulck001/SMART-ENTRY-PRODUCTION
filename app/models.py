from app import db
from datetime import datetime, timezone
import uuid


def utcnow():
    """Timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = 'users'

    id               = db.Column(db.Integer, primary_key=True)
    qr_uuid          = db.Column(db.String(36), unique=True, nullable=False,
                                 default=lambda: str(uuid.uuid4()))
    name             = db.Column(db.String(100), nullable=False)
    role             = db.Column(db.String(50), nullable=False)   # Student | Staff | Intern
    department       = db.Column(db.String(100), nullable=False)
    mobile_no        = db.Column(db.String(20), nullable=False)
    local_address    = db.Column(db.Text, nullable=False)
    default_transport = db.Column(db.String(50), nullable=True)
    is_active        = db.Column(db.Boolean, default=True, nullable=False)
    created_at       = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    logs = db.relationship('EntryLog', backref='user', lazy='dynamic',
                           cascade='all, delete-orphan')

    VALID_ROLES = {'Student', 'Staff', 'Intern'}
    VALID_TRANSPORT = {'Walking', 'Bicycle', 'Two-Wheeler', 'Car',
                       'Public Transit', 'Bus', 'Auto-Rickshaw', 'Other', 'Unknown'}

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'department': self.department,
            'mobile_no': self.mobile_no,
            'default_transport': self.default_transport,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EntryLog(db.Model):
    __tablename__ = 'entry_logs'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    timestamp      = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False,
                               index=True)
    transport_used = db.Column(db.String(100), nullable=True)
    vehicle_number = db.Column(db.String(50), nullable=True)
    entry_type     = db.Column(db.String(10), default='IN', nullable=False)  # IN | OUT
    scanned_by     = db.Column(db.String(50), nullable=True)  # Guard station / device ID

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'transport_used': self.transport_used,
            'vehicle_number': self.vehicle_number,
            'entry_type': self.entry_type,
        }


class Visitor(db.Model):
    __tablename__ = 'visitors'

    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(100), nullable=False)
    purpose   = db.Column(db.String(255), nullable=False)
    phone     = db.Column(db.String(20), nullable=False)
    added_by  = db.Column(db.String(50), nullable=True)
    host_name = db.Column(db.String(100), nullable=True)  # Who they're visiting
    id_proof  = db.Column(db.String(100), nullable=True)  # ID type shown
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False,
                          index=True)
    exit_time = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'purpose': self.purpose,
            'phone': self.phone,
            'added_by': self.added_by,
            'host_name': self.host_name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
        }
