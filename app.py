import streamlit as st
import spacy
import fitz  # PyMuPDF for handling PDF files
import pandas as pd
from datetime import datetime
import os
import ast  # To parse the string representation of the list
import re  # For regular expression matching
import base64

# Load a smaller spaCy model
nlp = spacy.load("en_pipeline")

CVS_FILE = "uploaded_cvs.csv"

# Function to save CV details to a CSV file
def save_cv_details(cvs):
    for cv in cvs:
        cv['output'] = repr(cv['output'])  # Convert list of tuples to string
    df = pd.DataFrame(cvs)
    df.to_csv(CVS_FILE, index=False)

# Function to load CV details from a CSV file
def load_cv_details():
    if os.path.exists(CVS_FILE):
        cvs = pd.read_csv(CVS_FILE).to_dict(orient="records")
        for cv in cvs:
            cv['output'] = ast.literal_eval(cv['output'])  # Convert string back to list of tuples
            if 'name' not in cv:
                cv['name'] = "Unknown"  # Handle missing names
        return cvs
    else:
        return []

# Function to clear all uploaded CVs
def clear_all_cvs():
    if os.path.exists(CVS_FILE):
        os.remove(CVS_FILE)
    st.session_state.cvs = []
    st.session_state.cvs_processed = 0

# Initialize session state for tracking
if 'cvs' not in st.session_state:
    st.session_state.cvs = load_cv_details()
    st.session_state.cvs_processed = len(st.session_state.cvs)
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def parse_cv(cv_path):
    try:
        doc = fitz.open(cv_path)
        text = ''
        for page in doc:
            text += page.get_text()

        text = text.strip()
        text = " ".join(text.split())
        doc = nlp(text)
        output = [(ent.label_, ent.text) for ent in doc.ents]

        # Extract the name of the person from the CV
        name = "Unknown"
        for label, entity in output:
            if label == "PERSON":
                name = entity
                break

        # Calculate the score based on the parsed data
        score, found_skills, years = calculate_score(output, text)

        return output, name, score, found_skills, years
    except Exception as e:
        st.error(f"Error processing the CV: {e}")
        return None, None, 0, [], 0

def search_parameter(output, parameter):
    if output is None:
        st.warning("No output to search. Please check if the CV file is valid.")
        return [], 0

    found_items = []
    count = 0
    for label, text in output:
        if parameter.lower() in text.lower():
            found_items.append((label, text))
            count += 1
    return found_items, count

def calculate_score(output, text):
    score = 0

    # Extract years of experience from the entire text
    experience_match = re.search(r'(\d+)\s+years of experience', text, re.IGNORECASE)
    years = 0
    if experience_match:
        years = int(experience_match.group(1))
        score += years * 2

    # List of skills to search for in the text
    skills = [
        "Machine Learning", "Natural Language Processing", "Big Data Handling",
        "AI", "Software Engineering", "Python", "Java", "C++", "JavaScript", "SQL",
        "C#", "Ruby", "PHP", "Swift", "Kotlin", "Django", "Flask", "React", "Angular",
        "Vue.js", "TensorFlow", "PyTorch", "Scikit-learn", "Spring", "ASP.NET", "Git",
        "Docker", "Kubernetes", "Jenkins", "AWS", "Azure", "Google Cloud", "Hadoop",
        "Spark", "Terraform", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle",
        "Microsoft SQL Server", "Data Analysis", "Deep Learning", "Data Visualization",
        "Cybersecurity", "Cloud Computing", "DevOps", "Blockchain", "Communication",
        "Teamwork", "Problem Solving", "Leadership", "Time Management", "Adaptability",
        "Critical Thinking", "Creativity", "Interpersonal Skills", "Project Management"
    ]

    # Calculate score based on skills found in the text
    found_skills = set()  # Using set to ensure each skill is counted only once
    for skill in skills:
        if re.search(fr'\b{skill}\b', text, re.IGNORECASE):
            found_skills.add(skill)

    skills_count = len(found_skills)
    skills_score = skills_count * 2
    score += skills_score  # Add 2 points for each found skill

    return score, list(found_skills), years

def sort_cvs(cvs, order='desc'):
    if order == 'desc':
        return sorted(cvs, key=lambda cv: cv['score'], reverse=True)
    elif order == 'asc':
        return sorted(cvs, key=lambda cv: cv['score'])
    elif order == 'newest':
        return sorted(cvs, key=lambda cv: cv['upload_time'], reverse=True)
    elif order == 'oldest':
        return sorted(cvs, key=lambda cv: cv['upload_time'])

def main():
    st.set_page_config(page_title="CV Parser App", layout="wide")

    st.title("CV Parser App")

    menu = ["Home", "Admin Dashboard"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Admin Dashboard" and not st.session_state.authenticated:
        st.subheader("Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == "admin" and password == "password":
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Incorrect username or password")
        return

    if choice == "Home":
        name = st.text_input("Enter your name")
        email = st.text_input("Enter your email")
        phone = st.text_input("Enter your phone number")
        uploaded_file = st.file_uploader("Upload a CV", type=["pdf"])

        if uploaded_file and email and phone and name:
            # Generate an integer ID for the CV
            cv_id = st.session_state.cvs_processed + 1
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_name = uploaded_file.name

            # Save uploaded file on disk to use with PyMuPDF
            temp_cv_path = f"temp_cv_{cv_id}.pdf"
            with open(temp_cv_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            output, parsed_name, score, found_skills, years = parse_cv(temp_cv_path)

            if output:
                st.success("Thank you for Applying, Have a nice day!")

                # Update session state with CV information
                cv_details = {
                    'id': cv_id,
                    'name': name,  # Use the entered name
                    'email': email,  # Add email to the details
                    'phone': phone,  # Add phone to the details
                    'output': output,  # Directly store the output
                    'upload_time': upload_time,
                    'score': score,  # Store the calculated score
                    'found_skills': found_skills,  # Store the found skills
                    'years': years,  # Store the years of experience
                    'file_path': temp_cv_path  # Store the path to the uploaded CV
                }
                st.session_state.cvs.append(cv_details)
                st.session_state.cvs_processed += 1

                # Save the updated CV details
                save_cv_details(st.session_state.cvs)

    elif choice == "Admin Dashboard" and st.session_state.authenticated:
        st.subheader("Admin Dashboard")
        
        # Reload CV details to ensure the latest data is reflected
        st.session_state.cvs = load_cv_details()
        st.session_state.cvs_processed = len(st.session_state.cvs)

        # Display the total number of CVs processed
        st.metric(label="Total CVs Processed", value=len(st.session_state.cvs))

        # Search bar to find CV by name with recommendations
        search_name = st.text_input("Search CV by name", key="search_name")
        all_names = [cv['name'] for cv in st.session_state.cvs]
        recommended_names = [name for name in all_names if search_name.lower() in name.lower()]

        if search_name:
            selected_name = st.selectbox("Recommended Names", options=recommended_names, key="recommended_names")
        else:
            selected_name = None

        if selected_name:
            filtered_cvs = [cv for cv in st.session_state.cvs if selected_name == cv['name']]
        else:
            filtered_cvs = [cv for cv in st.session_state.cvs if search_name.lower() in cv['name'].lower()]

        # Sort CVs by score or upload time
        sort_order = st.selectbox("Sort CVs by", ["Highest to Lowest Score", "Lowest to Highest Score", "Newest Upload", "Oldest Upload"])
        if sort_order == "Highest to Lowest Score":
            filtered_cvs = sort_cvs(filtered_cvs, order='desc')
        elif sort_order == "Lowest to Highest Score":
            filtered_cvs = sort_cvs(filtered_cvs, order='asc')
        elif sort_order == "Newest Upload":
            filtered_cvs = sort_cvs(filtered_cvs, order='newest')
        elif sort_order == "Oldest Upload":
            filtered_cvs = sort_cvs(filtered_cvs, order='oldest')

        # Display the uploaded CVs
        st.subheader("Uploaded CVs")
        for cv in filtered_cvs:
            with st.expander(f"CV ID: {cv['id']}   |   Name: {cv['name']}   |   Score: {cv['score']}   |   Date: {cv['upload_time']}"):
                st.markdown(f"**Email:** {cv['email']}")
                st.markdown(f"**Phone:** {cv['phone']}")
                st.markdown("**Detailed Analysis:**")
                seen = set()
                for item in cv['output']:
                    if len(item) == 2:  # Ensure there are two elements to unpack
                        label, text = item
                        if (label, text) not in seen:
                            st.markdown(f"- **{label}**: {text}")
                            seen.add((label, text))
                    else:
                        st.error(f"Invalid data: {item}")

                # Add a link to download the CV
                cv_file_path = cv.get('file_path', '')
                if cv_file_path and isinstance(cv_file_path, str) and os.path.exists(cv_file_path):
                    with open(cv_file_path, "rb") as f:
                        st.download_button(
                            label="Download CV",
                            data=f,
                            file_name=f"CV_{cv['name']}.pdf",
                            mime="application/pdf"
                        )

                    # Add a button to view the CV
                    if st.button(f"View CV {cv['id']}"):
                        st.markdown(f"**View CV:**")
                        with open(cv_file_path, "rb") as f:
                            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="500" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)

        # Button to clear all uploaded CVs
        if st.button("Clear All Uploaded CVs"):
            clear_all_cvs()
            st.experimental_rerun()  # Refresh the app to reflect changes

if __name__ == "__main__":
    main()
