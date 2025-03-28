from collections import defaultdict, OrderedDict
import csv
import os
import re
from uuid import uuid4
from flask import jsonify, render_template, request, redirect, url_for, flash, session
from app import app
from models.models import Scores, db, User, Subject, Chapter, Quiz, Questions
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
from sqlalchemy import distinct, func
from sqlalchemy.orm import joinedload
    
def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to continue')
            return redirect(url_for('login'))
    return inner  

def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user.is_admin:
            flash('You are not authorized to access this page')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return inner

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Please fill out all fields', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=username).first()

    if not user:
        flash('Username does not exist', 'danger')
        return redirect(url_for('login'))
    
    if not check_password_hash(user.passhash, password):
        flash('Incorrect password', 'danger')
        return redirect(url_for('login'))
    
    session['user_id'] = user.id
    session['is_admin'] = user.is_admin  

    flash('Login successful', 'success')
    return redirect(url_for('index'))


@app.route('/register')
def register():
    return render_template( 'register.html')

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    email = request.form.get('email')
    fullName = request.form.get('fullName')
    qualification = request.form.get('qualification')
    dob = request.form.get('dob')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not username or not password or not confirm_password or not email:
        flash('Please fill out all required fields')
        return redirect(url_for('register'))

    if password != confirm_password:
        flash('Passwords do not match')
        return redirect(url_for('register'))

    # Validate email format
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        flash('Invalid email format')
        return redirect(url_for('register'))

    # Check if the username or email already exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        flash('Username or Email already exists')
        return redirect(url_for('register'))

    # Hash the password
    password_hash = generate_password_hash(password)

    # Convert DOB to datetime.date and check if it is in the future
    try:
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
        if dob >= datetime.today().date():
            flash("Date of Birth cannot be in the future")
            return redirect(url_for('register'))
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.")
        return redirect(url_for('register'))

    # Create new user instance
    new_user = User(
        username=username,
        passhash=password_hash,
        fullName=fullName,
        email=email
    )

    db.session.add(new_user)
    db.session.commit()

    flash('Registration successful! Please log in.')
    return redirect(url_for('login'))  

@app.route('/profile')
@auth_required
def profile():
        user = User.query.get(session['user_id'])
        return render_template('profile.html', user=user)

@app.route('/profile', methods=['POST'])
@auth_required
def profile_post():
    username = request.form.get('username')
    cpassword = request.form.get('cpassword')
    password = request.form.get('password')
    email = request.form.get('email')
    fullName = request.form.get('fullName')

    if not username or not cpassword or not password:
        flash('Please fill out all the required fields')
        return redirect(url_for('profile'))

    user = User.query.get(session['user_id'])
    if not check_password_hash(user.passhash, cpassword):
        flash('Incorrect password')
        return redirect(url_for('profile'))
    
    if username !=user.username:
        new_username = User.query.filter_by(username=username).first()
        if new_username:
            flash('Username already exists')
            return redirect(url_for('profile'))
        
    new_password_hash = generate_password_hash(password)
    user.username = username
    user.passhash = new_password_hash
    user.email = email
    user.fullName = fullName    
    db.session.commit()
    flash('Profile updated successfully')
    return redirect(url_for('profile'))    


@app.route('/logout')
@auth_required
def logout():
     session.pop('user_id')
     return redirect(url_for('login'))

# ----Admin Routes ----

@app.route('/admin/admin')
@admin_required
def admin():
    subjects = Subject.query.all()
    
    # Fetch subject names and their chapter counts
    subject_names = [subject.name for subject in subjects]
    subject_sizes = [len(subject.chapters) for subject in subjects]

    # Fetch quiz count per subject
    quiz_counts = []
    question_counts = []

    for subject in subjects:
        quizzes = Quiz.query.join(Chapter).filter(Chapter.subject_id == subject.id).all()
        quiz_counts.append(len(quizzes))

        # Count questions for all quizzes in this subject
        total_questions = sum(len(quiz.questions) for quiz in quizzes)
        question_counts.append(total_questions)

    return render_template(
        'admin/admin.html',
        subjects=subjects,
        subject_names=subject_names,
        subject_sizes=subject_sizes,
        quiz_counts=quiz_counts,
        question_counts=question_counts 
    )


@app.route('/subject/add')
@admin_required
def add_subject():
    return render_template('subject/add.html')

@app.route('/subject/add', methods=['POST'])
@admin_required
def add_subject_post():
    name = request.form.get('name')
    description = request.form.get('description')

    if not name:
        flash('Please fill out all fields')
        return redirect(url_for('add_subject'))

    subject = Subject(name=name, description=description)
    db.session.add(subject)
    db.session.commit()
    flash('Subject added successfully.')
    return redirect(url_for('admin'))

@app.route('/subject/<int:id>/')
@admin_required
def show_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist')
        return redirect(url_for('admin'))
    return render_template('subject/show.html', subject=subject)

@app.route('/subject/<int:id>/edit')
@admin_required
def edit_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist')
        return redirect(url_for('admin'))
    return render_template('subject/edit.html', subject=subject)

@app.route('/subject/<int:id>/edit', methods=['POST'])
@admin_required
def edit_subject_post(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist')
        return redirect(url_for('admin'))
    
    name = request.form.get('name')
    description = request.form.get('description')

    if not name:
        flash('Please fill out all fields')
        return redirect(url_for('edit_subject', id=id))
    
    subject.name = name
    subject.description = description
    db.session.commit()
    flash('Subject updated successfully.')
    return redirect(url_for('admin'))

@app.route('/subject/<int:id>/delete')
@admin_required
def delete_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist.')
        return redirect(url_for('admin'))
    return render_template('/subject/delete.html', subject=subject)

@app.route('/subject/<int:id>/delete', methods=['POST'])
@admin_required
def delete_subject_post(id):
    subject = Subject.query.get(id)
    if not subject:
        flash('Subject does not exist.')
        return redirect(url_for('admin'))
    db.session.delete(subject)
    db.session.commit()

    flash('Subject deleted successfully')
    return redirect(url_for('admin'))


@app.route('/chapter/add/<int:subject_id>')
@admin_required
def add_chapter(subject_id):
    subjects = Subject.query.all()
    subject = Subject.query.get(subject_id)
    
    if not subject:
        flash('Subject does not exist.', 'danger')
        return redirect(url_for('admin'))

    return render_template('chapter/add.html', subject=subject, subjects=subjects, selected_subject_id=subject_id)


@app.route('/chapter/add/', methods=['POST'])
@admin_required
def add_chapter_post():
    name = request.form.get('name')
    description = request.form.get('description')
    subject_id = request.form.get('subject_id')

    # Ensure subject_id is valid
    if not subject_id:
        flash('Please select a subject.', 'danger')
        return redirect(url_for('add_chapter', subject_id=subject_id))

    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject does not exist.', 'danger')
        return redirect(url_for('admin'))

    if not name:
        flash('Please fill out all fields.', 'danger')
        return redirect(url_for('add_chapter', subject_id=subject_id))

    # Create a new chapter with subject_id
    chapter = Chapter(name=name, description=description, subject_id=subject.id)
    db.session.add(chapter)
    db.session.commit()

    flash('Chapter added successfully.', 'success')
    return redirect(url_for('show_subject', id=subject_id))


@app.route('/chapter/edit/<int:id>')
@admin_required
def edit_chapter(id):
    subjects = Subject.query.all()
    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist.')
        return redirect(url_for('admin'))
    return render_template('chapter/edit.html', subjects=subjects, chapter=chapter)

@app.route('/chapter/edit/<int:id>', methods=['POST'])
@admin_required
def edit_chapter_post(id):
    name = request.form.get('name')
    description = request.form.get('description')
    subject_id = request.form.get('subject_id')

    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject does not exist.')
        return redirect(url_for('admin'))

    if not name:
        flash('Please fill out all fields')
        return redirect(url_for('edit_chapter', id=id))

    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist.')
        return redirect(url_for('admin'))

    chapter.name = name
    chapter.description = description
    chapter.subject = subject
    db.session.commit()

    flash('Chapter updated successfully')
    return redirect(url_for('show_subject', id=subject_id))

@app.route('/chapter/<int:id>/delete')
@admin_required
def delete_chapter(id):
    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist.')
        return redirect(url_for('admin'))
    return render_template('chapter/delete.html', chapter=chapter)
    
@app.route('/chapter/<int:id>/delete', methods=['POST'])
@admin_required
def delete_chapter_post(id):
    chapter = Chapter.query.get(id)
    if not chapter:
        flash('Chapter does not exist.')
        return redirect(url_for('admin'))

    subject_id = chapter.subject.id
    db.session.delete(chapter)
    db.session.commit()

    flash('Chapter deleted successfully')
    return redirect(url_for('show_subject', id=subject_id))

@app.route('/admin/summary')
@admin_required
def summary():
    # Get number of chapters per subject
    subjects_chapters = (
        db.session.query(Subject.name, db.func.count(Chapter.id))
        .join(Chapter)
        .group_by(Subject.name)
        .all()
    )

    # Calculate the average score per subject
    average_scores_data = (
        db.session.query(Subject.name, db.func.avg(Scores.total_scored))
        .join(Chapter, Subject.id == Chapter.subject_id)
        .join(Quiz, Chapter.id == Quiz.chapter_id)
        .join(Scores, Quiz.id == Scores.quiz_id)
        .group_by(Subject.name)
        .all()
    )

    # Get the number of quiz attempts per subject
    quiz_attempts = (
        db.session.query(Subject.name, db.func.count(Scores.id))
        .join(Chapter, Subject.id == Chapter.subject_id)
        .join(Quiz, Chapter.id == Quiz.chapter_id)
        .join(Scores, Quiz.id == Scores.quiz_id)
        .group_by(Subject.name)
        .all()
    )

    # Convert data to dictionary/lists for JSON rendering
    subjects_chapters_dict = {subject: count for subject, count in subjects_chapters}
    subjects_scores = [subject for subject, _ in average_scores_data]
    average_scores = [round(avg_score, 2) for _, avg_score in average_scores_data]  # Rounded to 2 decimal places
    subjects_attempts = [subject for subject, _ in quiz_attempts]
    attempts_count = [count for _, count in quiz_attempts]

    return render_template(
        "admin/summary.html",
        subjects_chapters=list(subjects_chapters_dict.keys()),
        chapters_count=list(subjects_chapters_dict.values()),
        subjects_scores=subjects_scores,
        average_scores=average_scores,  # Updated key
        subjects_attempts=subjects_attempts,
        attempts_count=attempts_count
    )

@app.route('/quiz')
@admin_required
def quiz():
    all_quiz = Quiz.query.all()
    return render_template('quiz/index.html', quizzes=all_quiz)

@app.route('/quiz/add', methods=['GET', 'POST'])
@admin_required
def add_quiz():
    chapters = Chapter.query.all()  
    current_date = date.today().strftime('%Y-%m-%d')  

    if request.method == 'POST':
        chapter_id = request.form['chapter_id']
        date_of_quiz = request.form['date_of_quiz']
        time_duration = request.form['time_duration']
        remarks = request.form['remarks']

        # Convert date string to Python date object
        date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()

        # Prevent past dates
        if date_of_quiz < date.today():
            flash("Quiz date cannot be in the past!", "danger")
            return redirect(url_for('add_quiz'))

        new_quiz = Quiz(
            chapter_id=chapter_id,
            date_of_quiz=date_of_quiz,
            time_duration=time_duration,
            remarks=remarks
        )

        db.session.add(new_quiz)
        db.session.commit()
        flash('Quiz added successfully!', 'success')
        return redirect(url_for('quiz'))

    return render_template('quiz/add.html', chapters=chapters, current_date=current_date)

@app.route('/quiz/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    chapters = Chapter.query.all()  
    current_date = date.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        quiz.chapter_id = request.form['chapter_id']
        date_of_quiz = request.form['date_of_quiz']
        quiz.time_duration = request.form['time_duration']
        quiz.remarks = request.form['remarks']

        # Convert date string to Python date object
        date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()

        # Prevent past dates
        if date_of_quiz < date.today():
            flash("Quiz date cannot be in the past!", "danger")
            return redirect(url_for('edit_quiz', id=quiz.id))

        quiz.date_of_quiz = date_of_quiz
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('quiz'))

    return render_template('quiz/edit.html', quiz=quiz, chapters=chapters, current_date=current_date)


@app.route('/quiz/<int:id>/delete', methods=['GET'])
@admin_required
def delete_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    return render_template('quiz/delete.html', quiz=quiz)

@app.route('/quiz/<int:id>/delete', methods=['POST'])
@admin_required
def delete_quiz_post(id):
    quiz = Quiz.query.get_or_404(id)

    db.session.delete(quiz)
    db.session.commit()

    flash('Quiz deleted successfully!', 'success')
    return redirect(url_for('quiz'))


@app.route('/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@admin_required
def add_question(quiz_id):
    if request.method == 'POST':
        question_heading = request.form['question_heading']
        question_statement = request.form['question_statement']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form.get('option3', '')
        option4 = request.form.get('option4', '')
        correct_option = request.form['correct_option']

        new_question = Questions(
            quiz_id=quiz_id,
            question_heading=question_heading,  
            question_statement=question_statement,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_option=correct_option
        )

        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('quiz'))

    return render_template('quiz/add_question.html', quiz_id=quiz_id)

@app.route('/quiz/question/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(id):
    question = Questions.query.get_or_404(id)

    if request.method == 'POST':
        # Ensure all required form fields are present
        question.question_heading = request.form.get('question_heading', '').strip()
        question.question_statement = request.form.get('question_statement', '').strip()
        question.option1 = request.form.get('option1', '').strip()
        question.option2 = request.form.get('option2', '').strip()
        question.option3 = request.form.get('option3', '').strip()
        question.option4 = request.form.get('option4', '').strip()
        question.correct_option = request.form.get('correct_option', '').strip()

        # Validate required fields
        if not question.question_heading or not question.question_statement or not question.option1 or not question.option2 or not question.correct_option:
            flash("All required fields must be filled!", "danger")
            return redirect(request.url)  # Reload the form

        db.session.commit()
        flash(f'Question "{question.question_heading}" updated successfully!', 'success')
        return redirect(url_for('quiz'))  # Redirect to quiz page

    return render_template('quiz/edit_question.html', question=question)


@app.route('/quiz/question/<int:id>/delete', methods=['GET'])
@admin_required
def delete_question(id):
    question = Questions.query.get(id)
    return render_template('quiz/delete_question.html', question=question)

@app.route('/quiz/question/<int:id>/delete', methods=['POST'])
@admin_required
def delete_question_post(id):
    question = Questions.query.get(id)
    question_heading = question.question_heading  

    db.session.delete(question)
    db.session.commit()

    flash(f'Question "{question_heading}" deleted successfully!', 'success')
    return redirect(url_for('quiz'))


@app.route('/admin/users')
@admin_required
def users():
    users = (
        db.session.query(User)
        .options(joinedload(User.scores).joinedload(Scores.quiz).joinedload(Quiz.chapter).joinedload(Chapter.subject))
        .filter(User.is_admin == False)  
        .all()
    )

    user_data = []

    for user in users:
        quizzes = []
        for score in user.scores:
            total_marks = len(score.quiz.questions)  
            quiz_data = {
                "quiz_id": score.quiz_id,
                "quiz_name": f"{score.quiz_id} - {score.quiz.chapter.subject.name}",  
                "chapter_name": score.quiz.chapter.name,  
                "score": score.total_scored,
                "total_marks": total_marks
            }
            quizzes.append(quiz_data)

        user_data.append({
            "username": user.username,
            "fullname": user.fullName,
            "quizzes": quizzes
        })

    return render_template('admin/users.html', users=user_data)

# ----User routes--- #

@app.route('/')
@auth_required
def index():
    user = User.query.get(session['user_id'])

    # Redirect admin users to admin dashboard
    if user.is_admin:
        return redirect(url_for('admin'))

    # Fetch all upcoming quizzes with subject and chapter
    upcoming_quizzes = (
        db.session.query(
            Quiz.id,
            Quiz.date_of_quiz,
            Quiz.time_duration,
            db.func.count(Questions.id).label("num_questions"),
            Subject.name.label("subject_name"),
            Chapter.name.label("chapter_name")
        )
        .join(Chapter, Quiz.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .outerjoin(Questions, Quiz.id == Questions.quiz_id)
        .group_by(Quiz.id, Subject.name, Chapter.name)
        .order_by(Quiz.date_of_quiz.asc())
        .all()
    )

    # Get all subjects and chapters for dropdown filters
    subjects = Subject.query.order_by(Subject.name).all()
    chapters = Chapter.query.order_by(Chapter.name).all()

    return render_template(
        'user/index.html',
        upcoming_quizzes=upcoming_quizzes,
        subjects=subjects,
        chapters=chapters
    )

@app.route('/user/view/<int:quiz_id>')
@auth_required
def view(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)  # Get quiz or show 404 if not found
    return render_template('user/view.html', quiz=quiz)

@app.route('/user/start_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@auth_required
def start_quiz(quiz_id):
    user_id = session.get('user_id')
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Questions.query.filter_by(quiz_id=quiz.id).all()
    
    if not questions:
        flash("No questions available for this quiz!", "warning")
        return redirect(url_for('index'))
    
    return render_template('user/start_quiz.html', 
                         quiz=quiz, 
                         questions=questions,
                         total_questions=len(questions), 
                         time_duration=quiz.time_duration)


@app.route('/get_question/<int:quiz_id>/<int:question_index>')
@auth_required
def get_question(quiz_id, question_index):
    questions = Questions.query.filter_by(quiz_id=quiz_id).all()
    
    if question_index >= len(questions):
        return jsonify({'status': 'end'})
    
    question = questions[question_index]
    
    return jsonify({
        'status': 'ok',
        'id': question.id,
        'question_statement': question.question_statement,
        'options': [
            question.option1,
            question.option2,
            question.option3,
            question.option4
        ]
    })


@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@auth_required
def submit_quiz(quiz_id):
    user_id = session.get('user_id')  # Get the logged-in user ID
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Questions.query.filter_by(quiz_id=quiz_id).all()

    # Retrieve user's answers from the form
    user_answers = {}
    for question in questions:
        selected_option = request.form.get(f'question_{question.id}')
        user_answers[question.id] = selected_option  # Store as string for comparison

    # Calculate score and classify answers
    total_score = 0
    all_questions = {}

    for question in questions:
        correct_option_text = getattr(question, f'option{question.correct_option}')  # Get correct option text
        is_correct = user_answers.get(question.id) == str(question.correct_option)

        # Store question and its options
        all_questions[question.id] = {
            "question_statement": question.question_statement,
            "options": [
                {"id": "1", "text": question.option1, "is_correct": question.correct_option == 1},
                {"id": "2", "text": question.option2, "is_correct": question.correct_option == 2},
                {"id": "3", "text": question.option3, "is_correct": question.correct_option == 3},
                {"id": "4", "text": question.option4, "is_correct": question.correct_option == 4}
            ]
        }

        if is_correct:
            total_score += 1

    # Save the score in the database
    new_score = Scores(
        quiz_id=quiz.id,
        user_id=user_id,
        total_scored=total_score
    )
    db.session.add(new_score)
    db.session.commit()

    return render_template(
        'user/submit_quiz.html',
        quiz=quiz,
        all_questions=all_questions,
        user_answers=user_answers,
        total_score=total_score,
        total_questions=len(questions)
    )

@app.route('/user/scores')
@auth_required
def scores():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)

    # Query scores with explicit joins
    scores = (
        db.session.query(
            Scores.total_scored, 
            Scores.time_stamp_of_attempt, 
            Quiz.id.label("quiz_id"), 
            Chapter.name.label("chapter_name"), 
            Subject.name.label("subject_name"),
            Quiz.id,  
        )
        .join(Quiz, Scores.quiz_id == Quiz.id)
        .join(Chapter, Quiz.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .filter(Scores.user_id == user_id)
        .all()
    )

    # Calculate total_marks dynamically (Assuming each question = 1 mark)
    scores_data = []
    for score in scores:
        quiz = Quiz.query.get(score.quiz_id)  
        total_marks = len(quiz.questions)  
        
        scores_data.append({
            "quiz_id": score.quiz_id,
            "subject_name": score.subject_name,
            "chapter_name": score.chapter_name,
            "total_scored": score.total_scored,
            "total_marks": total_marks,
            "time_stamp_of_attempt": score.time_stamp_of_attempt,
            "num_questions": total_marks,  
        })

    # Get unique subjects and chapters for filter dropdowns
    subjects = Subject.query.all()
    chapters = Chapter.query.all()

    return render_template('user/scores.html', scores=scores_data, subjects=subjects, chapters=chapters)

@app.route('/user/summary_user')
@auth_required
def summary_user():
    user_id = session.get('user_id')

    # Query all quiz attempts for the user, ordered by most recent attempt.
    all_scores = (
        db.session.query(
            Scores,
            Quiz.id, 
            Scores.total_scored, 
            Scores.time_stamp_of_attempt, 
            Subject.name
        )
        .join(Quiz, Scores.quiz_id == Quiz.id)
        .join(Chapter, Quiz.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .filter(Scores.user_id == user_id)
        .order_by(Scores.time_stamp_of_attempt.desc())
        .all()
    )

    # Bar chart data: count total quiz attempts per subject.
    subject_wise_count = defaultdict(int)
    for score_obj, quiz_id, total_scored, timestamp, subject_name in all_scores:
        subject_wise_count[subject_name] += 1

    # Pie chart data: Select the latest attempt per subject
    latest_attempts = {}
    for score_obj, quiz_id, total_scored, timestamp, subject_name in all_scores:
        if subject_name not in latest_attempts:
            latest_attempts[subject_name] = (quiz_id, total_scored)

    # Prepare data for pie chart
    pie_subjects = []
    percentages = []
    
    for subject, (quiz_id, total_scored) in latest_attempts.items():
        total_questions = db.session.query(Questions).filter(Questions.quiz_id == quiz_id).count()
        max_score = total_questions * 100  
        percentage = (total_scored / max_score) * 100 if max_score > 0 else 0

        pie_subjects.append(subject)
        percentages.append(round(percentage, 2))

    return render_template(
        'user/summary_user.html',
        subjects=list(subject_wise_count.keys()),
        quiz_counts=list(subject_wise_count.values()),
        pie_subjects=pie_subjects,
        percentages=percentages
    )
