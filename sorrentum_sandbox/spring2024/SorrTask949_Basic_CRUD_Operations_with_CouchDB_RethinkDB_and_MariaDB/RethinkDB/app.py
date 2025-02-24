from flask import Flask, render_template, request, redirect, url_for
import rethinkdb as r
import os

app = Flask(__name__)

# Get RethinkDB host and port from environment variables 
RDB_HOST = os.getenv('RDB_HOST', 'rethinkdb')  
RDB_PORT = int(os.getenv('RDB_PORT', 28015))
DB_NAME = 'students_rethinkdb'

# Ensure the database and tables are set up
def db_setup():
    connection = r.r.connect(host=RDB_HOST, port=RDB_PORT)
    db_list = r.r.db_list().run(connection)
    if DB_NAME not in db_list:
        r.r.db_create(DB_NAME).run(connection)
    
    connection.use(DB_NAME)
    table_list = r.r.db(DB_NAME).table_list().run(connection)
    if 'students' not in table_list:
        r.r.db(DB_NAME).table_create('students').run(connection)
    connection.close()

db_setup()

# Connection details for RethinkDB
r.r.connect(RDB_HOST, RDB_PORT).repl()

# Check if database exists
db_list = r.r.db_list().run()
if 'students_rethinkdb' not in db_list:
    r.r.db_create('students_rethinkdb').run()

# Connect to the database
r_conn = r.r.connect(RDB_HOST, RDB_PORT, db='students_rethinkdb').repl()

# Check if table exists
table_list = r.r.db('students_rethinkdb').table_list().run()
if 'students' not in table_list:
    r.r.db('students_rethinkdb').table_create('students').run()


@app.route('/')
def index_rethinkdb():
    students = list(r.r.db(DB_NAME).table('students').run(r_conn))
    return render_template('index_rethinkdb.html', students=students)

@app.route('/add_rethinkdb', methods=['GET'])
def add_student_rethinkdb():
    return render_template('add_student_rethinkdb.html')

@app.route('/create_rethinkdb', methods=['POST'])
def create_rethinkdb():
    student = {
        'name': request.form['name'],
        'age': request.form['age']
    }
    r.r.db(DB_NAME).table('students').insert(student).run(r_conn)
    return redirect(url_for('index_rethinkdb'))

@app.route('/update_rethinkdb/<doc_id>', methods=['GET', 'POST'])
def update_rethinkdb(doc_id):
    student = r.r.db(DB_NAME).table('students').get(doc_id).run(r_conn)
    if request.method == 'POST':
        update_data = {
            'name': request.form['name'],
            'age': request.form['age']
        }
        r.r.db(DB_NAME).table('students').get(doc_id).update(update_data).run(r_conn)
        return redirect(url_for('index_rethinkdb'))
    return render_template('update_student_rethinkdb.html', student=student, doc_id=doc_id)

@app.route('/delete_rethinkdb/<doc_id>')
def delete_rethinkdb(doc_id):
    r.r.db(DB_NAME).table('students').get(doc_id).delete().run(r_conn)
    return redirect(url_for('index_rethinkdb'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
