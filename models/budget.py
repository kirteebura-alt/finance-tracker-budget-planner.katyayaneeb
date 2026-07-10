from extensions import db

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    category = db.Column(db.String(100), nullable=False)

    monthly_limit = db.Column(db.Float, nullable=False)