from flask import Flask, render_template, request, redirect, session, flash, g
from flask_socketio import SocketIO, emit
import sqlite3, threading
import os
from datetime import datetime
from time import sleep

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app)
DATABASE = os.path.abspath('StudentConnect_Flask/myapp/student_connect.db')

# Function to get the database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraint
    return db

# Function to check if a user exists
def user_exists(username, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM Class_info WHERE username = ? AND password = ?", (username, password))
    result = cursor.fetchone()
    return result[0] > 0

# Function to get the user ID from the username
def get_user_id(username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM Class_info WHERE username = ?", (username,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None
    
# Function to close the database connection at the end of the request
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
        if user_exists(username, password):
            flash('User already exists. Please log in.', 'error')
            return redirect('/login')

        if '@shibaura-it.ac.jp' in email:
            pass
        else:
            flash('Please use your Shibaura Institute of Technology email.', 'error')
            return redirect('/sign_up')

        # Create a new user
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)",
                       (subject, username, password, email))
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
        if user_exists(username, password):
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
        cursor.execute("UPDATE Class_info SET username = ? WHERE username = ?", (new_username, current_username))
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
        cursor.execute("UPDATE Class_info SET password = ? WHERE username = ?", (new_password, current_username))
        db.commit()
        flash('Password changed successfully.', 'success')
        return redirect('/login')
    return render_template('change_password.html')

# Channel page
@app.route('/channel', methods=['GET', 'POST'])
def channel():
    if 'username' not in session:
        return redirect('/login')
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        if 'channel_name' in request.form:
            channel_name = request.form['channel_name']
            # Check existing channel names to prevent duplicates
            cursor.execute("SELECT COUNT(*) FROM Channel WHERE name = ? AND subject = ?", (channel_name, session['subject']))
            result = cursor.fetchone()
            if result[0] > 0:
                flash('Channel name already exists.', 'error')
            else:
                # Get the user ID
                user_id = get_user_id(session['username'])
                # Register the channel
                cursor.execute("INSERT INTO Channel (name, created_by, subject) VALUES (?, ?, ?)", (channel_name, user_id, session['subject']))
                db.commit()
                flash('Channel created successfully.', 'success')
                socketio.emit('channel_created', {'channel_name': channel_name})
        else:
            channel_id = request.form['channel_id']
            if 'delete' in request.form:
                # Delete the channel
                cursor.execute("DELETE FROM Channel WHERE id = ?", (channel_id,))
                db.commit()
                flash('Channel deleted successfully.', 'success')
                socketio.emit('channel_deleted', {'channel_id': channel_id})

            elif 'select' in request.form:
                selected_channel = request.form.get('select')
                channel_id, channel_name = selected_channel.split(':')
                return redirect('/message?channel_id=' + channel_id + '&channel_name=' + channel_name)

    # Fetch the channels based on the subject
    cursor.execute("SELECT * FROM Channel WHERE subject = ?", (session['subject'],))
    channels = cursor.fetchall()
    return render_template('channel.html', channels=channels)

# Function to get the username from the user ID
def get_username(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM Class_info WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

@app.before_request
def register_jinja_globals():
    app.jinja_env.globals['get_username'] = get_username

# Message page
@app.route('/message', methods=['GET', 'POST'])
def message():
    if 'username' not in session:
        return redirect('/login')
    if request.method == 'POST':
        message_content = request.form['message_content']
        channel_id = request.args.get('channel_id')
        channel_name = request.args.get('channel_name')

        db = get_db()
        cursor = db.cursor()

        if message_content.startswith('Q. '):
            new_channel_name = message_content[3:]
            cursor.execute("INSERT INTO Channel (name, subject) VALUES (?, ?)", (new_channel_name, session['subject']))
            db.commit()
            flash('Channel created successfully.', 'success')
            socketio.emit('channel_created', {'channel_name': new_channel_name})
            return redirect('/channel')
        else:
            user_id = get_user_id(session['username'])
            cursor.execute("INSERT INTO Message (channel_id, user_id, content, subject) VALUES (?, ?, ?, ?)",
                           (channel_id, user_id, message_content, session['subject']))
            db.commit()
            flash('Message posted successfully.', 'success')
            socketio.emit('message_posted', {'channel_id': channel_id})

    channel_id = request.args.get('channel_id')
    channel_name = request.args.get('channel_name')

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Message WHERE channel_id = ? AND subject = ?", (channel_id, session['subject']))
    messages = cursor.fetchall()

    return render_template('message.html', channel_id=channel_id, channel_name=channel_name, messages=messages)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Debugging purposes
@app.route('/view_database')
def view_database():
    db = get_db()
    cursor = db.cursor()
    # Get the contents of the Class_info table
    cursor.execute("SELECT * FROM Class_info;")
    class_info_rows = cursor.fetchall()

    # Get the contents of the Channel table
    cursor.execute("SELECT * FROM Channel;")
    channel_rows = cursor.fetchall()
    # Get the contents of the Message table
    cursor.execute("SELECT * FROM Message;")
    message_rows = cursor.fetchall()
    return render_template('view_database.html', class_info_rows=class_info_rows, channel_rows=channel_rows, message_rows=message_rows)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
