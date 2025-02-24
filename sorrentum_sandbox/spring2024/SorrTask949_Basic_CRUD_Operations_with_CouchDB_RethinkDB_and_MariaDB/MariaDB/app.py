from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import errors

def get_db_connection(retry_num=5, delay=5):
    """Attempt to connect to the database with retries."""
    for attempt in range(retry_num):
        try:
            conn = mysql.connector.connect(
                host='mariadb',
                user='root',
                password='1971',
                database='students_mariadb'
            )
            print("Database connection successful.")
            return conn
        except mysql.connector.Error as err:
            print(f"Database connection failed: {err}")
            time.sleep(delay)  # wait before retrying
    raise Exception("Failed to connect to the database after several attempts.")


app = Flask(__name__)

@app.before_first_request
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                age INT NOT NULL
            );
        """)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error creating table: {err}")
    finally:
        cursor.close()
        conn.close()


# MariaDB configuration
config = {
    'user': 'root',
    'password': '1971',
    'host': 'mariadb',  # Use service name defined in docker-compose
    'database': 'students_mariadb',
    'raise_on_warnings': True
}

# Function to get a new database connection
def get_db_connection():
    conn = mysql.connector.connect(**config)
    return conn

def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        age INT NOT NULL
    );
    """
    cursor.execute(create_table_query)
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index_mariadb():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index_mariadb.html', students=students)

@app.route('/add_mariadb', methods=['GET'])
def add_student_mariadb():
    return render_template('add_student_mariadb.html')

@app.route('/create_mariadb', methods=['POST'])
def create_mariadb():
    conn = get_db_connection()
    cursor = conn.cursor()
    name = request.form['name']
    age = request.form['age']
    query = "INSERT INTO students (name, age) VALUES (%s, %s)"
    cursor.execute(query, (name, age))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index_mariadb'))

@app.route('/update_mariadb/<int:student_id>', methods=['GET', 'POST'])
def update_mariadb(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        query = "UPDATE students SET name = %s, age = %s WHERE id = %s"
        cursor.execute(query, (name, age, student_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index_mariadb'))
    else:
        query = "SELECT * FROM students WHERE id = %s"
        cursor.execute(query, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('update_student_mariadb.html', student=student)

@app.route('/delete_mariadb/<int:student_id>')
def delete_mariadb(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM students WHERE id = %s"
    cursor.execute(query, (student_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index_mariadb'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)