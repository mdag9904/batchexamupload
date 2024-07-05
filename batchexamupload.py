import streamlit as st
import os
import requests
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

def extract_course_assignment_ids(assignment_url):
    parts = assignment_url.split('/')
    course_id = parts[4]
    assignment_id = parts[6]
    return course_id, assignment_id

def main():
    st.title("Canvas Batch Exam Upload")

    api_url = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com/")
    api_key = st.text_input("Canvas API Key", type="password")
    assignment_url = st.text_input("Assignment Link")
    suffix = st.text_input("File Suffix (Optional)", "")
    
    uploaded_files = st.file_uploader("Choose PDF files", type="pdf", accept_multiple_files=True)
    
    if st.button("Upload PDFs") and uploaded_files:
        course_id, assignment_id = extract_course_assignment_ids(assignment_url)
        canvas = Canvas(api_url, api_key)

        def initiate_file_upload(file_path, user_id, file_name_with_suffix):
            """Initiate file upload for a submission."""
            url = f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/files"
            headers = {
                'Authorization': f'Bearer {api_key}'
            }
            response = requests.post(url, headers=headers, data={
                'name': file_name_with_suffix,
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

        # Process each uploaded file
        for uploaded_file in uploaded_files:
            original_file_name = uploaded_file.name
            user_id = original_file_name.replace('.pdf', '')  # Extract Canvas user ID from filename
            file_name_with_suffix = f"{user_id}-{suffix}.pdf" if suffix else original_file_name

            with open(file_name_with_suffix, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            if os.path.exists(file_name_with_suffix):
                try:
                    # Initiate file upload
                    upload_initiation_response = initiate_file_upload(file_name_with_suffix, user_id, file_name_with_suffix)
                    upload_url = upload_initiation_response['upload_url']
                    upload_params = upload_initiation_response['upload_params']

                    # Upload the file
                    file_id = upload_file(upload_url, upload_params, file_name_with_suffix)
                    st.success(f"Uploaded file for student {user_id}, file ID: {file_id}")

                    # Submit the assignment
                    submission_response = submit_assignment(user_id, file_id)
                    st.success(f"Submitted for student {user_id}")
                except CanvasException as e:
                    st.error(f"Failed to upload/submit for student {user_id}: {e}")
                finally:
                    os.remove(file_name_with_suffix)
            else:
                st.warning(f"File not found for user ID {user_id}")

        st.info("All uploads processed.")

if __name__ == "__main__":
    main()
