from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import os
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Ensure this is set for sessions to work

# PostgreSQL connection details
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')

# Google Cloud Storage details
GCP_BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')


# Connect to PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

# Upload file to GCP
def upload_to_gcp(bucket_name, source_file_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    try:
        blob.upload_from_filename(source_file_name)
        print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    except Exception as e:
        print(f"Failed to upload file to GCP: {e}")
        raise
    
    return blob.public_url

def list_bucket_contents():
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(GCP_BUCKET_NAME)
    
    for blob in blobs:
        print(blob.name)



# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
            return render_template('invalid_credentials.html')
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM job_applications')
    applications = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_dashboard.html', applications=applications)

@app.route('/approve_application/<int:id>')
def approve_application(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE job_applications SET status = %s WHERE id = %s', ('Approved', id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/reject_application/<int:id>')
def reject_application(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE job_applications SET status = %s WHERE id = %s', ('Rejected', id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/add_job_role', methods=['GET', 'POST'])
def add_job_role():
    if request.method == 'POST':
        role_name = request.form['role_name']
        description = request.form['description']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO job_roles (role_name, description) VALUES (%s, %s)', (role_name, description))
        conn.commit()
        cur.close()
        conn.close()
        flash('Job role added successfully')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM job_roles')
    roles = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_job_role.html', roles=roles)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/hr_login', methods=['GET', 'POST'])
def hr_login():
    # HR login logic here
    return 'HR login page placeholder'

@app.route('/candidate_login', methods=['GET', 'POST'])
def candidate_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM candidate WHERE email = %s AND password = %s', (email, password))
        candidate = cur.fetchone()
        cur.close()
        conn.close()

        if candidate:
            session['candidate_logged_in'] = True
            session['candidate_id'] = candidate[0]
            return redirect(url_for('job_descriptions'))
        else:
            flash('Invalid credentials')
            return render_template('invalid_credentials.html')

    return render_template('candidate_login.html')

@app.route('/candidate_register', methods=['GET', 'POST'])
def candidate_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        country = request.form['country']
        value1 = request.form['value1']
        value2 = request.form['value2']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO candidate (name, email, password, country, value1, value2) VALUES (%s, %s, %s, %s, %s, %s)',
                    (name, email, password, country, value1, value2))
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('candidate_login'))

    return render_template('candidate_register.html')

@app.route('/job_billboard')
def job_billboard():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT role_name FROM job_roles')
    job_roles = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('job_billboard.html', job_roles=job_roles)

@app.route('/apply_job', methods=['POST'])
def apply_job():
    name = request.form['name']
    email = request.form['email']
    position = request.form['position']
    resume = request.files['resume']
    
    # Ensure the resumes directory exists
    if not os.path.exists('resumes'):
        os.makedirs('resumes')
    
    # Save resume temporarily
    resume_path = os.path.join('resumes', resume.filename)
    resume.save(resume_path)
    
    # Upload resume to GCP
    gcp_resume_url = upload_to_gcp(GCP_BUCKET_NAME, resume_path, resume.filename)
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO job_applications (name, email, position, resume_path) VALUES (%s, %s, %s, %s)',
                (name, email, position, gcp_resume_url))
    conn.commit()
    cur.close()
    conn.close()

    flash('Your application has been submitted successfully.')
    return redirect(url_for('thank_you'))

@app.route('/job_descriptions')
def job_descriptions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM job_roles')
    roles = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('job_descriptions.html', roles=roles)


@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    app.run(debug=True, port=80)
