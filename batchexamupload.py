import streamlit as st
import os
import requests
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException

def main():
    st.title("Canvas Batch Exam Upload")

    api_url = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com/")
    api_key = st.text_input("Canvas API Key", type="password")
    course_id = st.number_input("Course ID", value=26075)
    assignment_id = st.number_input("Assignment ID", value=359794)
    pdf_directory = st.text_input("PDF Directory", "/Users/markdagher_1/Downloads/Exams")

    if st.button("Upload PDFs"):
        canvas = Canvas(api_url, api_key)

        def initiate_file_upload(file_path, user_id):
            """Initiate file upload for a submission."""
            url = f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/files"
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

        # Upload files to the assignment submission context
        for file_name in os.listdir(pdf_directory):
            if file_name.endswith('.pdf'):
                file_path = os.path.join(pdf_directory, file_name)
                user_id = file_name.replace('.pdf', '')  # Extract Canvas user ID from filename

                if os.path.exists(file_path):
                    try:
                        # Initiate file upload
                        upload_initiation_response = initiate_file_upload(file_path, user_id)
                        upload_url = upload_initiation_response['upload_url']
                        upload_params = upload_initiation_response['upload_params']

                        # Upload the file
                        file_id = upload_file(upload_url, upload_params, file_path)
                        st.success(f"Uploaded file for student {user_id}, file ID: {file_id}")
                    except CanvasException:
                        st.error(f"Failed to upload for student {user_id}")
                else:
                    st.warning(f"File not found for user ID {user_id}")

        st.info("All uploads processed.")

if __name__ == "__main__":
    main()
