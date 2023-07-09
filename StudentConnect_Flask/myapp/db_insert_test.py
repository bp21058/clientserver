import sqlite3

def insert_class_info(subject, username, password, email):
    conn = sqlite3.connect('test_db.db')
    cursor = conn.cursor()

    query = "INSERT INTO Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)"
    values = (subject, username, password, email)
    cursor.execute(query, values)

    conn.commit()
    cursor.close()
    conn.close()

# 使用例
subject = "5261"
username = "user1"
password = "password1"
email = "user1@example.com"

insert_class_info(subject, username, password, email)
