from datetime import datetime
from extensions import db


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(db.Float, nullable=False)

    category = db.Column(db.String(100), nullable=False)

    transaction_type = db.Column(db.String(20), nullable=False)

    notes = db.Column(db.String(255))

    is_recurring = db.Column(db.Boolean,default=False
    )
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )