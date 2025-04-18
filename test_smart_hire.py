import os
import unittest
from unittest.mock import patch, MagicMock
from flask import url_for
from app import app, get_db_connection
import pytest
from io import BytesIO

class TestSmartHire(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['SERVER_NAME'] = 'localhost'

        with self.app.app_context():
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('DELETE FROM job_applications WHERE email = %s', ('testcandidate@example.com',))
            cur.execute('DELETE FROM candidate WHERE email = %s', ('testcandidate@example.com',))
            cur.execute('DELETE FROM job_roles WHERE role_name = %s', ('Test Role',))
            cur.execute('DELETE FROM job_roles WHERE role_name = %s', ('New Job Title',))
            conn.commit()
            cur.close()
            conn.close()

    def tearDown(self):
        # Clean up database after each test
        with self.app.app_context():
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('DELETE FROM job_applications WHERE email = %s', ('testcandidate@example.com',))
            cur.execute('DELETE FROM candidate WHERE email = %s', ('testcandidate@example.com',))
            cur.execute('DELETE FROM job_roles WHERE role_name = %s', ('Test Role',))
            cur.execute('DELETE FROM job_roles WHERE role_name = %s', ('New Job Title',))
            conn.commit()
            cur.close()
            conn.close()

    def test_home_page(self):
        result = self.client.get('/')
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Smart Hire Vision', result.data)

    def test_admin_login(self):
        result = self.client.post('/admin_login', data=dict(username='admin', password='password'), follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Admin Dashboard', result.data)
        

    def test_candidate_registration(self):
        result = self.client.post('/candidate_register', data=dict(
            name='Test Candidate',
            email='testcandidate@example.com',
            password='password123',
            country='Country',
            value1='Value 1',
            value2='Value 2'
        ), follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Candidate Login', result.data)
    def test_candidate_login(self):
        with self.app.app_context():
            # Register the candidate before attempting to log in
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO candidate (name, email, password, country, value1, value2) VALUES (%s, %s, %s, %s, %s, %s)',
                        ('Test Candidate', 'testcandidate@example.com', 'password123', 'Country', 'Value 1', 'Value 2'))
            conn.commit()
            cur.close()
            conn.close()

        # Attempt to log in with valid credentials
        result = self.client.post('/candidate_login', data=dict(email='testcandidate@example.com', password='password123'), follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Job Descriptions', result.data)
    
    
    def test_job_descriptions_page(self):
       
        with self.app.app_context():
            # Insert test job roles into the test database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO job_roles (role_name, description) VALUES (%s, %s)', ('Test Role', 'Test Description'))
            conn.commit()
            cur.close()
            conn.close()

            # Test accessing the job descriptions page
            response = self.client.get(url_for('job_descriptions'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Job Descriptions", response.data)
            self.assertIn(b"Test Role", response.data)

    # @patch('app.get_db_connection')
    # def test_apply_job(self, mock_get_db_connection):
    #     # Mock the database connection
    #     mock_conn = MagicMock()
    #     mock_get_db_connection.return_value = mock_conn

    #     with self.client.session_transaction() as sess:
    #         sess['email'] = 'testcandidate@example.com'

    #     # Ensure the directory exists
    #     os.makedirs('resumes', exist_ok=True)

    #     # Ensure the file path is correct
    #     resume_path = os.path.join('resumes', 'test_resume.pdf')

    #     # Create the resume file
    #     with open(resume_path, 'wb') as resume_file:
    #         resume_file.write(b'my resume content')

    #     with open(resume_path, 'rb') as resume_file:
    #         data = {
    #             'name': 'Test Candidate',
    #             'email': 'testcandidate@example.com',
    #             'position': 'Test Role',
    #             'resume': (resume_file, 'test_resume.pdf')
    #         }

    #         result = self.client.post(url_for('apply_job'), data=data, content_type='multipart/form-data', follow_redirects=True)
    #         self.assertEqual(result.status_code, 200)
    #         self.assertIn(b"Your application has been submitted successfully.", result.data)

    #     # Clean up the resume file
    #     os.remove(resume_path)

    def test_manage_roles(self):
        with self.client.session_transaction() as sess:
            sess['admin_logged_in'] = True
        
        result = self.client.post('/add_job_role', data=dict(
            role_name='New Job Title',
            description='Job Description'
        ), follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Job role added successfully', result.data)

        # Verify that the new job role appears in the roles list on the same page
        self.assertIn(b'New Job Title', result.data)

    @patch('app.get_db_connection')
    def test_admin_dashboard(self, mock_get_db_connection):
        # Mock the database connection
        mock_conn = MagicMock()
        mock_get_db_connection.return_value = mock_conn

        with self.client.session_transaction() as sess:
            sess['admin'] = True

        result = self.client.get('/admin_dashboard', follow_redirects=True)
        
        if result.status_code == 302:
            print(f"Redirection to: {result.headers['Location']}")

        print(result.data.decode())  # Print the HTML content for debugging
        
        self.assertEqual(result.status_code, 200)

    def test_logout(self):
        with self.client.session_transaction() as sess:
            sess['email'] = 'testcandidate@example.com'
        
        result = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b'Smart Hire Vision', result.data)

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM job_applications WHERE email = %s', ('testcandidate@example.com',))
        conn.commit()
        cur.close()
        conn.close()

if __name__ == '__main__':
    unittest.main()
