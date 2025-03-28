from datetime import datetime
from app import app
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String[32], unique=True)
    passhash = db.Column(db.String[256], nullable=False)
    fullName = db.Column(db.String[64], nullable=True)
    email = db.Column(db.String[64], unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    scores = db.relationship('Scores', backref='user', lazy=True, cascade='all, delete-orphan')

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String[32], unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    chapters = db.relationship('Chapter', backref='subject', lazy=True, cascade='all, delete-orphan')

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    name = db.Column(db.String[32], unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    quizes = db.relationship('Quiz', backref='chapter', lazy=True, cascade='all, delete-orphan')
    
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False, default=datetime.utcnow)  
    time_duration = db.Column(db.String(5), nullable=False) 
    remarks = db.Column(db.Text, nullable=True)

    questions = db.relationship('Questions', backref='quiz', lazy=True, cascade='all, delete-orphan')
    scores = db.relationship('Scores', backref='quiz', lazy=True, cascade='all, delete-orphan')

class Questions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_heading = db.Column(db.String(255), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)  
    option1 = db.Column(db.String(255), nullable=False)  
    option2 = db.Column(db.String(255), nullable=False)  
    option3 = db.Column(db.String(255), nullable=True)   
    option4 = db.Column(db.String(255), nullable=True)   
    correct_option = db.Column(db.Integer, nullable=False)

class Scores(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    time_stamp_of_attempt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_scored = db.Column(db.Integer, nullable=False, default=0)    


with app.app_context():
    db.create_all()

    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        password_hash = generate_password_hash('admin')
        admin = User(username='admin', email='admin@gmail.com', fullName='Admin', passhash=password_hash, is_admin=True)
        db.session.add(admin)
        db.session.commit()