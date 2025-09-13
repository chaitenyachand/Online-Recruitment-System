import streamlit as st
import mysql.connector
import pandas as pd
import hashlib
import PyPDF2
import plotly.express as px
from datetime import datetime

# --- Section 1: Database Connection and Setup ---
st.set_page_config(
    page_title="Online Recruitment System",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👨‍💼 Online Recruitment System")
st.markdown("---")

# IMPORTANT: Update these with your MySQL database details.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root', # Replace with your MySQL username
    'password': 'Charu1414@#', # Replace with your MySQL password
    'database': 'recruitment_db'
}

def get_db_connection():
    """Establishes and returns a connection to the MySQL database."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        st.error(f"Error connecting to MySQL database: {err}")
        return None

def create_tables():
    """Creates the necessary tables if they do not exist."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # User table with roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('applicant', 'recruiter', 'admin') NOT NULL
            )
        """)
        
        # Jobs table with new fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recruiter_id INT NOT NULL,
                company VARCHAR(255) NOT NULL,
                job_role VARCHAR(255) NOT NULL,
                job_description TEXT NOT NULL,
                skills_required TEXT,
                salary VARCHAR(255),
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recruiter_id) REFERENCES users(id)
            )
        """)

        # Applications table with new applicant details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id INT NOT NULL,
                applicant_id INT NOT NULL,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(20),
                gender VARCHAR(50),
                nationality VARCHAR(100),
                resume_text TEXT,
                status ENUM('Pending', 'In Review', 'Interview', 'Rejected', 'Hired') DEFAULT 'Pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (applicant_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()

# Create tables on startup
create_tables()

# --- Section 2: User Authentication and Management ---

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password, role):
    """Authenticates a user and returns their ID and role."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        password_hash = hash_password(password)
        cursor.execute("SELECT id, role FROM users WHERE username = %s AND password_hash = %s AND role = %s",
                       (username, password_hash, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    return None

def add_user(username, password, role):
    """Adds a new user to the database."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        try:
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                           (username, password_hash, role))
            conn.commit()
            st.success(f"User '{username}' registered successfully as a {role}!")
        except mysql.connector.Error as err:
            st.error(f"Error registering user: {err}")
        finally:
            cursor.close()
            conn.close()

# Use Streamlit's session state to manage user login status
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

def login_form():
    """Renders the login and registration form."""
    with st.container(border=True):
        st.subheader("Login or Register")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Login")
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_role = st.selectbox("Role", ["applicant", "recruiter", "admin"], key="login_role")
            
            if st.button("Log In"):
                user = authenticate_user(login_username, login_password, login_role)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user['id']
                    st.session_state.user_role = user['role']
                    st.rerun()
                else:
                    st.error("Invalid username, password, or role.")

        with col2:
            st.markdown("### Register")
            reg_username = st.text_input("New Username", key="reg_user")
            reg_password = st.text_input("New Password", type="password", key="reg_pass")
            reg_role = st.selectbox("Register as", ["applicant", "recruiter", "admin"], key="reg_role")
            
            if st.button("Register"):
                if reg_username and reg_password and reg_role:
                    add_user(reg_username, reg_password, reg_role)
                else:
                    st.warning("Please fill in all registration fields.")

def logout_button():
    """Renders the logout button."""
    if st.session_state.logged_in:
        st.sidebar.button("Logout", on_click=lambda: st.session_state.clear(), type="secondary")

# --- Section 3: Applicant Dashboard ---

def show_applicant_dashboard():
    """Renders the dashboard for applicants."""
    st.subheader(f"Welcome, {st.session_state.user_role.capitalize()}! 👋")
    st.markdown("---")
    
    conn = get_db_connection()
    if conn:
        jobs_df = pd.read_sql("SELECT * FROM jobs", conn)
        applied_jobs_df = pd.read_sql(f"SELECT job_id, status FROM applications WHERE applicant_id = {st.session_state.user_id}", conn)
        conn.close()

        if 'view_job_details' not in st.session_state:
            st.session_state.view_job_details = None
        
        if st.session_state.view_job_details is None:
            st.markdown("### Available Jobs")
            if not jobs_df.empty:
                cols = st.columns(3, gap="small")
                for i, row in jobs_df.iterrows():
                    with cols[i % 3]:
                        job_applied = row['id'] in applied_jobs_df['job_id'].values
                        with st.container(border=True):
                            st.subheader(row['company'])
                            st.write(f"**{row['job_role']}**")
                            if job_applied:
                                current_status = applied_jobs_df.loc[applied_jobs_df['job_id'] == row['id'], 'status'].iloc[0]
                                st.markdown(f"<p style='color:green; font-weight:bold;'>{current_status}</p>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<p style='color:black; font-weight:bold;'>Not Applied</p>", unsafe_allow_html=True)

                            if st.button("View Details & Apply", key=f"view_{row['id']}"):
                                st.session_state.view_job_details = row['id']
                                st.rerun()
            else:
                st.info("No jobs are currently available.")
        else:
            show_job_details(jobs_df)

def show_job_details(jobs_df):
    """Displays a single job's details and the application form."""
    st.markdown("### Job Details")
    selected_job = jobs_df[jobs_df['id'] == st.session_state.view_job_details].iloc[0]
    
    with st.container(border=True):
        st.subheader(selected_job['job_role'])
        st.markdown(f"**Company:** {selected_job['company']}")
        st.markdown(f"**Salary:** {selected_job['salary']}")
        st.markdown("---")
        st.markdown("### Job Description")
        st.write(selected_job['job_description'])
        st.markdown("---")
        st.markdown("### Skills Required")
        st.write(selected_job['skills_required'])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE job_id = %s AND applicant_id = %s",
                   (int(selected_job['id']), st.session_state.user_id))
    has_applied = cursor.fetchone()
    cursor.close()
    conn.close()

    if has_applied:
        st.success("You have already applied for this job.")
        if st.button("Withdraw Application", type="secondary"):
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM applications WHERE job_id = %s AND applicant_id = %s",
                               (int(selected_job['id']), st.session_state.user_id))
                conn.commit()
                st.success("Application withdrawn successfully!")
                cursor.close()
                conn.close()
                st.session_state.view_job_details = None
                st.rerun()
    else:
        st.markdown("### Apply for this Job")
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        gender = st.selectbox("Gender", ['Male', 'Female', 'Other'])
        nationality = st.text_input("Nationality")
        uploaded_file = st.file_uploader("Upload your resume (PDF/TXT)", type=["pdf", "txt"])
        
        if st.button("Submit Application"):
            if uploaded_file and name and email and phone and nationality:
                resume_text = ""
                if uploaded_file.name.endswith('.txt'):
                    try:
                        resume_text = uploaded_file.read().decode('utf-8')
                    except UnicodeDecodeError:
                        resume_text = uploaded_file.read().decode('latin-1')
                elif uploaded_file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    for page_num in range(len(pdf_reader.pages)):
                        resume_text += pdf_reader.pages[page_num].extract_text() or ''
                        
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO applications 
                        (job_id, applicant_id, name, email, phone, gender, nationality, resume_text) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (int(selected_job['id']), st.session_state.user_id, name, email, phone, gender, nationality, resume_text))
                    conn.commit()
                    st.success("Application submitted successfully!")
                    cursor.close()
                    conn.close()
                    st.session_state.view_job_details = None
                    st.rerun()
            else:
                st.warning("Please fill in all details and upload your resume.")
    
    if st.button("Back to Jobs"):
        st.session_state.view_job_details = None
        st.rerun()

# --- Section 4: Recruiter Dashboard ---

def show_recruiter_dashboard():
    """Renders the dashboard for recruiters."""
    st.subheader(f"Welcome, {st.session_state.user_role.capitalize()}! 👋")
    st.markdown("---")

    conn = get_db_connection()
    if conn:
        st.markdown("### Your Job Postings")
        my_jobs_df = pd.read_sql(f"SELECT id, title, company, job_role, job_description FROM jobs WHERE recruiter_id = {st.session_state.user_id}", conn)
        
        if not my_jobs_df.empty:
            jobs_to_delete = st.multiselect("Select job IDs to delete:", my_jobs_df['id'].tolist())
            if st.button("Delete Selected Jobs", type="secondary"):
                if jobs_to_delete:
                    cursor = conn.cursor()
                    for job_id in jobs_to_delete:
                        # First, delete all applications related to the job
                        cursor.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
                        # Then, delete the job itself
                        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
                    conn.commit()
                    st.success(f"Successfully deleted {len(jobs_to_delete)} jobs and their applications.")
                    st.rerun()

            st.dataframe(my_jobs_df.drop(columns=['job_description']), use_container_width=True)

            st.markdown("### View and Compare Applicants")
            job_id_to_view = st.number_input("Enter Job ID to view applicants:", min_value=1, step=1, key="rec_job_id")
            
            if st.button("View Applicants"):
                st.session_state.view_applicants = job_id_to_view
            
            if 'view_applicants' in st.session_state and st.session_state.view_applicants:
                applicants_df = pd.read_sql(f"""
                    SELECT 
                        a.id AS application_id,
                        u.username,
                        a.name,
                        a.email,
                        a.phone,
                        a.gender,
                        a.nationality,
                        a.status,
                        a.resume_text
                    FROM applications a
                    JOIN users u ON a.applicant_id = u.id
                    WHERE a.job_id = {st.session_state.view_applicants}
                """, conn)

                if not applicants_df.empty:
                    st.success(f"Applicants found for Job ID: {st.session_state.view_applicants}")
                    st.info(f"Total applicants: {len(applicants_df)}")
                    
                    st.markdown("#### Graphical Comparison of Applicants")
                    col_graphs = st.columns(3)
                    with col_graphs[0]:
                        gender_counts = applicants_df['gender'].value_counts()
                        fig_gender = px.pie(
                            names=gender_counts.index,
                            values=gender_counts.values,
                            title='Gender Distribution',
                            hole=0.4
                        )
                        st.plotly_chart(fig_gender, use_container_width=True)
                    
                    with col_graphs[1]:
                        nationality_counts = applicants_df['nationality'].value_counts()
                        fig_nationality = px.bar(
                            x=nationality_counts.index,
                            y=nationality_counts.values,
                            title='Nationality of Applicants',
                            labels={'x': 'Nationality', 'y': 'Number of Applicants'},
                            color=nationality_counts.index
                        )
                        st.plotly_chart(fig_nationality, use_container_width=True)
                    
                    with col_graphs[2]:
                        status_counts = applicants_df['status'].value_counts()
                        fig_status = px.pie(
                            names=status_counts.index,
                            values=status_counts.values,
                            title='Application Statuses',
                            hole=0.4
                        )
                        st.plotly_chart(fig_status, use_container_width=True)
                        
                    st.markdown("#### Candidate List")
                    st.dataframe(applicants_df[['name', 'email', 'phone', 'status', 'resume_text']], use_container_width=True)
                    
                    st.markdown("#### Manage Individual Applicants")
                    selected_applicant_name = st.selectbox("Select an applicant by name:", applicants_df['name'].unique())
                    
                    if selected_applicant_name:
                        selected_app = applicants_df[applicants_df['name'] == selected_applicant_name].iloc[0]
                        
                        st.write(f"**Viewing details for:** {selected_app['name']}")
                        
                        st.info("Applicant's resume is displayed below.")
                        st.text_area("Resume Content", value=selected_app['resume_text'], height=300)
                        
                        new_status = st.selectbox("Update Status:", ['Pending', 'In Review', 'Interview', 'Rejected', 'Hired'], index=['Pending', 'In Review', 'Interview', 'Rejected', 'Hired'].index(selected_app['status']))
                        
                        if st.button("Update Status"):
                            cursor = conn.cursor()
                            application_id_to_update = int(selected_app['application_id']) 
                            cursor.execute("UPDATE applications SET status = %s WHERE id = %s", (new_status, application_id_to_update))
                            conn.commit()
                            st.success(f"Status for {selected_applicant_name} updated to {new_status}!")
                            st.rerun()

                else:
                    st.info(f"No applicants have applied for Job ID {st.session_state.view_applicants} yet.")
        else:
            st.info("You have not posted any jobs yet.")
        
        st.markdown("---")
        st.markdown("### Post a New Job")
        with st.form("new_job_form"):
            company = st.text_input("Company Name")
            job_role = st.text_input("Job Role")
            job_description = st.text_area("Job Description")
            skills_required = st.text_area("Skills Required (e.g., Python, SQL, AWS)")
            salary = st.text_input("Salary Structure")
            
            submitted = st.form_submit_button("Post Job", type="primary")
            
            if submitted:
                if company and job_role and job_description and skills_required and salary:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO jobs (recruiter_id, title, company, job_role, job_description, skills_required, salary, description) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (st.session_state.user_id, job_role, company, job_role, job_description, skills_required, salary, job_description))
                    conn.commit()
                    st.success("Job posted successfully!")
                    st.rerun()
                else:
                    st.warning("Please fill in all fields to post a job.")

    conn.close()


# --- Section 5: Admin Dashboard ---

def show_admin_dashboard():
    """Renders the dashboard for the admin."""
    st.subheader(f"Welcome, {st.session_state.user_role.capitalize()}! 👋")

    conn = get_db_connection()
    if conn:
        st.markdown("### All Users")
        users_df = pd.read_sql("SELECT id, username, role FROM users", conn)
        st.dataframe(users_df, use_container_width=True)

        st.markdown("### All Job Postings")
        jobs_df = pd.read_sql("SELECT j.id, u.username AS recruiter, j.title, j.description FROM jobs j JOIN users u ON j.recruiter_id = u.id", conn)
        st.dataframe(jobs_df, use_container_width=True)

        st.markdown("### All Applications")
        applications_df = pd.read_sql("SELECT a.id, u.username AS applicant, j.title AS job_title, a.status FROM applications a JOIN users u ON a.applicant_id = u.id JOIN jobs j ON a.job_id = j.id", conn)
        st.dataframe(applications_df, use_container_width=True)

    conn.close()

# --- Main App Logic (Streamlit's "pages") ---

if not st.session_state.logged_in:
    login_form()
else:
    logout_button()
    if st.session_state.user_role == "applicant":
        show_applicant_dashboard()
    elif st.session_state.user_role == "recruiter":
        show_recruiter_dashboard()
    elif st.session_state.user_role == "admin":
        show_admin_dashboard()
