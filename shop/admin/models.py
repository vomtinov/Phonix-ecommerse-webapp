from shop import db, app  # import the Flask app to create context

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(180), nullable=False)
    profile = db.Column(db.String(180), nullable=False, default="profile.jpg")

    def __repr__(self):
        return f'<User {self.username}>'

# ✅ Use Flask's app context to create DB tables
with app.app_context():
    db.create_all()
