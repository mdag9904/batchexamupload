import streamlit as st
import os
import requests
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from pathlib import Path

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

    folder_selected = st.text_input("Path to folder containing PDFs")
    
    if st.button("Upload PDFs") and folder_selected:
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

        def get_existing_submission_files(user_id):
            """Get existing files for a submission."""
            submission_url = f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
            headers = {
                'Authorization': f'Bearer {api_key}'
            }
            response = requests.get(submission_url, headers=headers)

            if response.status_code != 200:
                return []

            submission_data = response.json()
            if 'attachments' in submission_data:
                return [attachment['id'] for attachment in submission_data['attachments']]
            else:
                return []

        def submit_assignment(user_id, file_ids):
            """Submit the assignment with the uploaded file IDs."""
            submission_url = f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
            submission_data = {
                'submission': {
                    'submission_type': 'online_upload',
                    'file_ids': file_ids
                },
                'as_user_id': user_id  # Submit on behalf of the student
            }
            submission_headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            submission_response = requests.post(submission_url, headers=submission_headers, json=submission_data)

            if submission_response.status_code != 200:
                raise CanvasException("Submission failed.")

            return submission_response.json()

        # Process each PDF file in the selected folder
        pdf_files = list(Path(folder_selected).glob("*.pdf"))
        for pdf_file in pdf_files:
            user_id = pdf_file.stem  # Extract Canvas user ID from filename
            file_name_with_suffix = f"{user_id}-{suffix}.pdf" if suffix else pdf_file.name

            if pdf_file.exists():
                try:
                    # Initiate file upload
                    upload_initiation_response = initiate_file_upload(pdf_file, user_id, file_name_with_suffix)
                    upload_url = upload_initiation_response['upload_url']
                    upload_params = upload_initiation_response['upload_params']

                    # Upload the file
                    file_id = upload_file(upload_url, upload_params, pdf_file)
                    st.success(f"Uploaded file for student {user_id}, file ID: {file_id}")

                    # Get existing submission files
                    existing_file_ids = get_existing_submission_files(user_id)
                    all_file_ids = existing_file_ids + [file_id]

                    # Submit the assignment with all files
                    submission_response = submit_assignment(user_id, all_file_ids)
                    st.success(f"Submitted for student {user_id}")
                except CanvasException as e:
                    st.error(f"Failed to upload/submit for student {user_id}: {e}")
            else:
                st.warning(f"File not found for user ID {user_id}")

        st.info("All uploads processed.")

if __name__ == "__main__":
    main()
