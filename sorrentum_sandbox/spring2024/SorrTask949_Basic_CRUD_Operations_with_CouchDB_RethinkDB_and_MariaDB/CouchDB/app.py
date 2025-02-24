from flask import Flask, request, render_template, redirect, url_for
import couchdb


app = Flask(__name__)

# Connect to CouchDB
couch = couchdb.Server('http://admin:1971@couchdb:5984/')
DB_User = '_users'
DB_NAME = 'students'


if DB_User in couch:
    db = couch[DB_User]
else:
    db = couch.create(DB_User)

# Ensure the database exists
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)



@app.route('/')
def index_couchdb():
    # Fetch all student entries
    students = db.view('_all_docs', include_docs=True)
    return render_template('index_couchdb.html', students=students)

@app.route('/add_couchdb', methods=['GET'])
def add_student_couchdb():
    return render_template('add_student_couchdb.html')

@app.route('/create_couchdb', methods=['POST'])
def create_couchdb():
    name = request.form['name']
    age = request.form['age']
    doc = {'name': name, 'age': age}
    db.save(doc)
    return redirect(url_for('index_couchdb'))

@app.route('/update_couchdb/<doc_id>', methods=['GET', 'POST'])
def update_couchdb(doc_id):
    doc = db[doc_id]
    if request.method == 'POST':
        doc['name'] = request.form['name']
        doc['age'] = request.form['age']
        db.save(doc)
        return redirect(url_for('index_couchdb'))
    return render_template('update_student_couchdb.html', doc=doc)


@app.route('/delete_couchdb/<doc_id>', methods=['GET'])
def delete_couchdb(doc_id):
    db.delete(db[doc_id])
    return redirect(url_for('index_couchdb'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)  # Ensure the host is set to '0.0.0.0'

