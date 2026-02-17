import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from fpdf import FPDF

# --- CONFIGURATION ---
# Replace this with your actual Spreadsheet ID (from the URL of your sheet)
SPREADSHEET_ID = "1y8SlCPHeeUHCi1o3vfjNhEF1bi2fQHtQ4NxHeRT_Blk" 
SHEET_NAME = "electivedata" # Matches your snippet

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- GOOGLE SHEETS CONNECTION ---
def get_service():
    """Authenticates and returns the Sheets API service."""
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def write_to_google_sheet(row_data):
    """Appends a row of data to the sheet."""
    service = get_service()
    if service:
        body = {"values": [row_data]}
        try:
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A1",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return True
        except Exception as e:
            st.error(f"Error writing to sheet: {e}")
            return False
    return False

def read_from_google_sheet():
    """Reads all data for the Admin Dashboard."""
    service = get_service()
    if service:
        try:
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                        range=f"{SHEET_NAME}!A:AA").execute() # Read cols A to AA
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame() # Return empty DF if no data

            # Convert list of lists to DataFrame
            # Assuming first row is headers
            headers = values[0]
            data = values[1:]
            
            # Ensure all rows have same length as headers (fill missing with empty string)
            # This prevents errors if some cells are empty at the end of a row
            padded_data = [row + [''] * (len(headers) - len(row)) for row in data]
            
            df = pd.DataFrame(padded_data, columns=headers)
            return df
        except Exception as e:
            st.error(f"Error reading from sheet: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- PDF GENERATOR (Same as before) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'STUDENT PROFILE & ACTIVITY RECORD', 0, 1, 'C') # [Source: 1]
        self.ln(5)

def generate_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # I. PERSONAL INFORMATION [Source: 2]
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'I. PERSONAL INFORMATION', 0, 1)
    
    pdf.set_font('Arial', '', 11)
    fields = [
        ("Name of Student", data.get('Name', '')),
        ("SIS ID", data.get('SIS ID', '')),
        ("Email ID", data.get('Email', '')),
        ("Year of Admission", data.get('Year', '')),
        ("Contact Address", data.get('Address', '')),
        ("Occupation of Father/Mother", data.get('Occupation', ''))
    ]
    
    for label, value in fields:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(60, 8, f"{label}:", 0, 0)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 8, str(value))

    pdf.ln(5)

    # II. ACADEMIC PERFORMANCE [Source: 9]
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'II. ACADEMIC PERFORMANCE', 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, 'Semester', 1, 0, 'C', 1)
    pdf.cell(60, 10, '% Marks / SGPA', 1, 0, 'C', 1)
    pdf.cell(90, 10, 'Remark', 1, 1, 'C', 1)
    
    pdf.set_font('Arial', '', 10)
    sems = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
    
    for sem in sems:
        # Access using dynamic keys like Sem_I_Marks
        mark = data.get(f'Sem_{sem}_Marks', '')
        remark = data.get(f'Sem_{sem}_Remark', '')
        
        pdf.cell(40, 8, sem, 1, 0, 'C')
        pdf.cell(60, 8, str(mark), 1, 0, 'C')
        pdf.cell(90, 8, str(remark), 1, 1, 'L')

    pdf.ln(5)

    # III. ACTIVITY & ACHIEVEMENT RECORD [Source: 11]
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'III. ACTIVITY & ACHIEVEMENT RECORD', 0, 1)
    
    activities = [
        ("Participation in Extracurricular Activities", "(Sports, Cultural, NSS, etc.)", data.get('Extracurricular', '')),
        ("Participation in Curricular Activities", "(Workshops, Seminars, Competitions, Hackathons)", data.get('Curricular', '')),
        ("Certifications & Technical Skill Development", "(NPTEL, AWS, RedHat, Professional Courses, etc.)", data.get('Certifications', '')),
        ("Internship & Placement Details", "(Company Name, Duration, Role)", data.get('Internship', '')),
        ("Project Undertaken", "(Title, Domain, Guide Name)", data.get('Projects', ''))
    ]

    for title, subtitle, content in activities:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, title, 0, 1)
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(0, 5, subtitle, 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, str(content) + "\n", 'B') 
        pdf.ln(3)

    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP UI ---
st.title("Student Profile Management System")

tab1, tab2 = st.tabs(["Student Entry Form", "Admin / Download List"])

with tab1:
    st.header("Fill Student Profile")
    
    with st.form("student_form"):
        # Section I
        st.subheader("I. Personal Information")
        col1, col2 = st.columns(2)
        name = col1.text_input("Name of Student")
        sis_id = col2.text_input("SIS ID")
        email = col1.text_input("Email ID")
        year = col2.text_input("Year of Admission")
        address = st.text_area("Contact Address")
        occupation = st.text_input("Occupation of Father/Mother")

        # Section II - Academic Table
        st.subheader("II. Academic Performance")
        st.write("Fill in your marks and remarks for each semester:")
        
        default_data = {
            "Semester": ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'],
            "% Marks / SGPA": [""] * 8,
            "Remark": [""] * 8
        }
        df_marks = pd.DataFrame(default_data)
        edited_df = st.data_editor(df_marks, hide_index=True, use_container_width=True)

        # Section III
        st.subheader("III. Activity & Achievement Record")
        extra = st.text_area("Participation in Extracurricular Activities")
        curric = st.text_area("Participation in Curricular Activities")
        certs = st.text_area("Certifications & Technical Skill Development")
        intern = st.text_area("Internship & Placement Details")
        proj = st.text_area("Project Undertaken")





        submitted = st.form_submit_button("Submit Profile")

        if submitted:
            if not name or not sis_id:
                st.error("⚠️ Name and SIS ID are required.")
            else:
                # --- NEW: CHECK FOR DUPLICATES ---
                existing_data = read_from_google_sheet()
                
                # Check if 'SIS ID' column exists and if the ID is already there
                if not existing_data.empty and 'SIS ID' in existing_data.columns:
                    # Convert to string to ensure accurate comparison (e.g., '123' vs 123)
                    existing_ids = existing_data['SIS ID'].astype(str).values
                    
                    if str(sis_id) in existing_ids:
                        st.error(f"❌ Error: A student with SIS ID '{sis_id}' has already submitted a profile!")
                        st.stop() # Stops the code here so it doesn't save

                # --- IF UNIQUE, PROCEED TO SAVE ---
                row_data = [
                    name, sis_id, email, year, address, occupation,
                    extra, curric, certs, intern, proj
                ]
                
                # Append marks to row data
                for index, row in edited_df.iterrows():
                    row_data.append(str(row['% Marks / SGPA']))
                    row_data.append(str(row['Remark']))

                success = write_to_google_sheet(row_data)
                
                if success:
                    st.success("✅ Profile Submitted Successfully!")
with tab2:
    st.header("Registered Students")
    
    # Load data using the new API method
    df = read_from_google_sheet()
    
    if not df.empty:
        st.dataframe(df)

        # Dropdown to select student
        # Check if 'Name' column exists to avoid errors
        if 'Name' in df.columns:
            student_to_download = st.selectbox("Select Student to Download PDF", df['Name'].unique())
            
            if st.button("Generate PDF"):
                # Filter data for selected student
                student_row = df[df['Name'] == student_to_download].iloc[0]
                
                # Convert row to dictionary for PDF function
                pdf_data = student_row.to_dict()
                
                # Generate and Download
                pdf_bytes = generate_pdf(pdf_data)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"{student_to_download}_Profile.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Data found, but 'Name' column is missing. Check your Sheet headers.")
    else:
        st.info("No records found or unable to connect.")