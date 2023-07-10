from flask import Flask, render_template, request, redirect, session, flash, g
from flask_socketio import SocketIO, emit
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app)

DATABASE = "student_connect.db"

# Function to get the database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraint
    return db

# Function to check if a user exists based on subject
def user_exists(subject, username, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM {}_Class_info WHERE username = ? AND password = ?".format(subject.replace(" ", "_")), (username, password))
    result = cursor.fetchone()
    return result[0] > 0

# Function to get the user ID from the username based on subject
def get_user_id(subject, username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM {}_Class_info WHERE username = ?".format(subject.replace(" ", "_")), (username,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

# Function to close the database connection at the end of the request based on subject
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

# Sign up page
@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        subject = request.form['subject']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if the user already exists
        if user_exists(subject, username, password):
            flash('User already exists. Please log in.', 'error')
            return redirect('/login')
        
        if '@shibaura-it.ac.jp' in email:
            flash('Please use your Shibaura Institute of Technology email.', 'error')
            return redirect('/sign_up')

        # Create a new user
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO {}_Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)".format(subject.replace(" ", "_")), (subject, username, password, email))
        db.commit()
        flash('Sign up successful. Please log in.', 'success')
        return redirect('/login')

    return render_template('sign_up.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        subject = request.form['subject']
        username = request.form['username']
        password = request.form['password']
        # Check if the user exists
        if user_exists(subject, username, password):
            # Successful login
            session['subject'] = subject
            session['username'] = username
            return redirect('/channel')
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

# Change username page
@app.route('/change_username', methods=['GET', 'POST'])
def change_username():
    if request.method == 'POST':
        subject = request.form['subject']
        current_username = request.form['current_username']
        new_username = request.form['new_username']
        # Get the database connection
        db = get_db()
        cursor = db.cursor()
        # Implement the update of the username in the Class_info table
        cursor.execute("UPDATE {}_Class_info SET username = ? WHERE username = ?".format(subject.replace(" ", "_")), (new_username, current_username))
        db.commit()
        flash('Username changed successfully.', 'success')
        return redirect('/login')
    return render_template('change_username.html')

# Change password page
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        subject = request.form['subject']
        current_username = request.form['current_username']
        new_password = request.form['new_password']
        # Get the database connection
        db = get_db()
        cursor = db.cursor()
        # Implement the update of the password in the Class_info table
        cursor.execute("UPDATE {}_Class_info SET password = ? WHERE username = ?".format(subject.replace(" ", "_")), (new_password, current_username))
        db.commit()
        flash('Password changed successfully.', 'success')
        return redirect('/login')
    return render_template('change_password.html')

# Channel page
@app.route('/channel', methods=['GET', 'POST'])
def channel():
    if 'username' not in session:
        return redirect('/login')

    subject = session['subject']

    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        if 'channel_name' in request.form:
            channel_name = request.form['channel_name']
            # Check existing channel names to prevent duplicates
            cursor.execute("SELECT COUNT(*) FROM {}_Channel WHERE name = ?".format(subject.replace(" ", "_")), (channel_name,))
            result = cursor.fetchone()
            if result[0] > 0:
                flash('Channel name already exists.', 'error')
            else:
                # Get the user ID
                user_id = get_user_id(subject, session['username'])

                # Register the channel
                cursor.execute("INSERT INTO {}_Channel (name, created_by) VALUES (?, ?)".format(subject.replace(" ", "_")), (channel_name, user_id))
                db.commit()
                flash('Channel created successfully.', 'success')
                socketio.emit('channel_created', {'channel_name': channel_name}, broadcast=True)
        else:
            channel_id = request.form['channel_id']

            if 'delete' in request.form:
                if channel_name == 'General':
                    flash('Cannot delete General channel.', 'error')
                    return redirect('/channel')
                # Delete the channel
                cursor.execute("DELETE FROM {}_Channel WHERE id = ?".format(subject.replace(" ", "_")), (channel_id,))
                db.commit()
                flash('Channel deleted successfully.', 'success')
                socketio.emit('channel_deleted', {'channel_id': channel_id}, broadcast=True)

            elif 'select' in request.form:
                selected_channel = request.form.get('select')
                channel_id, channel_name = selected_channel.split(':')
                return redirect('/message?channel_id=' + channel_id + '&channel_name=' + channel_name)

    cursor.execute("SELECT * FROM {}_Channel".format(subject.replace(" ", "_")))
    channels = cursor.fetchall()

    return render_template('channel.html', channels=channels)

# Function to get the username from the user ID based on subject
def get_username(subject, user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM {}_Class_info WHERE id = ?".format(subject.replace(" ", "_")), (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

@app.before_request
def register_jinja_globals():
    subject = session.get('subject')
    if subject:
        app.jinja_env.globals['get_username'] = get_username
        app.jinja_env.globals['subject'] = subject

# Message page
@app.route('/message', methods=['GET', 'POST'])
def message():
    if 'username' not in session:
        return redirect('/login')

    subject = session['subject']

    if request.method == 'POST':
        message_content = request.form['message_content']
        channel_id = request.args.get('channel_id')
        channel_name = request.args.get('channel_name')

        if message_content.startswith('Q. '):
            new_channel_name = message_content[3:]
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO {}_Channel (name) VALUES (?)".format(subject.replace(" ", "_")), (new_channel_name,))
            db.commit()
            flash('Channel created successfully.', 'success')
            socketio.emit('channel_created', {'channel_name': new_channel_name}, broadcast=True)
            return redirect('/channel')

        db = get_db()
        cursor = db.cursor()
        user_id = get_user_id(subject, session['username'])
        cursor.execute("INSERT INTO {}_Message (channel_id, user_id, content) VALUES (?, ?, ?)".format(subject.replace(" ", "_")), (channel_id, user_id, message_content))
        db.commit()
        flash('Message posted successfully.', 'success')
        socketio.emit('message_posted', {'channel_id': channel_id}, broadcast=True)

    channel_id = request.args.get('channel_id')
    channel_name = request.args.get('channel_name')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM {}_Message WHERE channel_id = ?".format(subject.replace(" ", "_")), (channel_id,))
    messages = cursor.fetchall()

    return render_template('message.html', channel_id=channel_id, channel_name=channel_name, messages=messages)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
