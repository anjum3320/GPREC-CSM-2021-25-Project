import MySQLdb
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template, redirect, flash, send_file, session, url_for
from sklearn.preprocessing import MinMaxScaler
import pickle
import re
import MySQLdb as mysqlclient

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load ML models
drug = pickle.load(open('models/drug.pkl', 'rb'))
dosage = pickle.load(open('models/dosage.pkl', 'rb'))
side = pickle.load(open('models/side.pkl', 'rb'))

# MySQL Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'drug'

mysql = MySQLdb.connect(
    host="localhost",
    user="root",
    password="root",
    database="drug"
)

mysql.autocommit(True)

# --------- Routes ---------
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')



@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        username = session['username']
        return render_template('dashboard.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s', (session['username'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    flash("You have been logged out successfully!", "info")
    return redirect(url_for('index'))

@app.route('/tracker')
def tracker():
    if 'loggedin' in session:
        return render_template('tracker.html')
    else:
        flash("Please login first to access the tracker!", "warning")
        return redirect(url_for('login'))

@app.route('/pharmacies')
def pharmacies():
    if 'loggedin' in session:
        return render_template('pharmacies.html')
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['username'] = account['username']
            return redirect(url_for('dashboard'))  # Redirecting to Dashboard
        else:
            flash('Incorrect username or password!')
    return render_template('login.html', msg=msg)




@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        age = request.form['age']

        print(f"Received data: {username}, {email}, {age}")  # Debugging

        reg = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,10}$"
        pattern = re.compile(reg)

        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM people WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
            flash(msg, 'error')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
            flash(msg, 'error')
        elif not re.match(r'^[A-Za-z0-9]+$', username):
            msg = 'Username must contain only letters and numbers!'
            flash(msg, 'error')
        elif not pattern.match(password):
            msg = 'Password must be 6-10 chars with special chars, numbers, and uppercase!'
            flash(msg, 'error')
        else:
            try:
                cursor.execute('INSERT INTO people (username, password, email, age) VALUES (%s, %s, %s, %s)',
                               (username, password, email, age))
                mysql.commit()  # Correct way to commit in MySQLdb
                print("✅ Data inserted successfully!")  # Debugging
                flash('You have successfully registered! Please login.', 'success')
                return redirect(url_for('login'))
            except MySQLdb.Error as e:
                print(f"❌ MySQL Error: {e}")
            finally:
                cursor.close()  # Ensure cursor is closed after execution

    # print("⚠️ Redirecting back to register page...")  # Debugging
    return render_template('register.html', msg=msg)


@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        try:
            # Collect 5 numerical features from form
            int_features = [float(x) for x in request.form.values()]
            final_features = [np.array(int_features)]  # Convert to NumPy array

            # Model Predictions
            drug_pred = drug.predict(final_features)
            dosage_pred = dosage.predict(final_features)
            side_pred = side.predict(final_features)

            dose = str(round(dosage_pred[0], 2))

            # Display result
            label = f"Drug: {drug_pred[0]}, Dosage: {dose} mg, Side-effects: {side_pred[0]}"
            return render_template('prediction.html', prediction_text=label)

        except Exception as e:
            return render_template('prediction.html', prediction_text=f"Error: {str(e)}")

    return render_template('prediction.html')

if __name__ == "__main__":
    app.run(debug=True)
