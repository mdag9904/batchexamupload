import os
import requests
import streamlit as st
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

# Define functions for the file upload process
def initiate_file_upload(file_path, user_id, course_id, assignment_id, api_key):
    """Initiate file upload for a submission."""
    url = f"https://canvas-parra.beta.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/files"
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    file_name = os.path.basename(file_path)
    response = requests.post(url, headers=headers, data={
        'name': file_name,
        'size': os.path.getsize(file_path),
        'content_type': 'application/pdf'
    })

    if response.status_code != 200:
        raise CanvasException("File upload initiation failed.")

    return response.json()

def upload_file(upload_url, upload_params, file_path):
    """Upload the file to the given URL with provided parameters."""
    with open(file_path, 'rb') as f:
        upload_response = requests.post(upload_url, data=upload_params, files={'file': f})

    if upload_response.status_code not in [200, 201, 302]:
        raise CanvasException("File upload failed.")

    location_url = upload_response.headers.get('Location')
    if location_url:
        return location_url.split('/')[-1]  # Extract ID from URL
    else:
        return upload_response.json().get('id')

def process_upload(api_key, assignment_link, pdf_directory):
    # Extract course_id and assignment_id from the assignment_link
    parts = assignment_link.split('/')
    course_id = parts[-3]
    assignment_id = parts[-1]

    # Initialize Canvas object
    canvas = Canvas("https://canvas-parra.beta.instructure.com/", api_key)

    # Upload files to the assignment submission context
    for file_name in os.listdir(pdf_directory):
        if file_name.endswith('.pdf'):
            file_path = os.path.join(pdf_directory, file_name)
            user_id = file_name.replace('.pdf', '')  # Extract Canvas user ID from filename

            if os.path.exists(file_path):
                try:
                    # Initiate file upload
                    upload_initiation_response = initiate_file_upload(file_path, user_id, course_id, assignment_id, api_key)
                    upload_url = upload_initiation_response['upload_url']
                    upload_params = upload_initiation_response['upload_params']

                    # Upload the file
                    file_id = upload_file(upload_url, upload_params, file_path)
                    st.success(f"Uploaded file for student {user_id}, file ID: {file_id}")

                except CanvasException as e:
                    st.error(f"Failed to upload for student {user_id}: {e}")
            else:
                st.warning(f"File not found for user ID {user_id}")

    st.info("All uploads processed.")

# Streamlit app layout
st.title("Canvas File Uploader")

api_key = st.text_input("API Key")
assignment_link = st.text_input("Assignment Link")
pdf_directory = st.text_input("PDF Directory")

if st.button("Start Upload"):
    if not api_key or not assignment_link or not pdf_directory:
        st.error("Please fill in all the required fields.")
    else:
        process_upload(api_key, assignment_link, pdf_directory)
