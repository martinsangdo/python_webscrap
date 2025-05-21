#Bridge between our app and LinkedIn
import os
from dotenv import load_dotenv
import requests
import time

# Get the absolute path to the directory where __init__.py is located
package_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the .env file
dotenv_path = os.path.join(package_dir, '.env')

# Load the .env file using the explicit path
load_dotenv(dotenv_path=dotenv_path)

LI_REST_URI = os.environ['LI_REST_URI']
LI_VERSION = os.environ['LI_VERSION']
LI_ACCESS_TOKEN = os.environ['LI_ACCESS_TOKEN']

li_headers = {
    'Authorization': LI_ACCESS_TOKEN,
    'LinkedIn-Version': LI_VERSION,
    'X-RestLi-Protocol-Version': '2.0.0',
    'Content-Type': 'application/json'
}

#register an upload link to LI
def get_upload_link_document(li_page_id):
    url = LI_REST_URI + 'documents?action=initializeUpload'
    payload = {
        "initializeUploadRequest": {
            "owner": "urn:li:organization:" + li_page_id
        }
    }
    try:
        detail = requests.post(url, json=payload, headers=li_headers)
        # {
        #     "value": {
        #         "uploadUrlExpiresAt": 1650567510704,
        #         "uploadUrl": "https://www.linkedin.com/dms-uploads/D5510AQHXjcP8QBYD9A/ads-uploadedDocument/0?ca=vector_ads&cn=uploads&sync=0&v=beta&ut=36ezHi_Pod5aM1",
        #         "document": "urn:li:document:C5F10AQGKQg_6y2a4sQ"
        #     }
        # }
        return detail.json()
    except Exception as e:
        print(e)
        return {'error': e}
#
def upload_pdf(file_path, upload_url):
    #upload the doc https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/documents-api?view=li-lms-2025-04&tabs=curl#sample-curl-request
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (file.name, file, 'application/pdf')}
            headers = {
                'Authorization': LI_ACCESS_TOKEN,
                'LinkedIn-Version': LI_VERSION
            }

            response = requests.post(upload_url, files=files, headers=headers)
            print("Status Code:", response.status_code)
            print("Headers:", response.headers)
            print("Response Body:", response.text)

            if response.status_code >= 200 and response.status_code < 300:
                print("File uploaded successfully!")
                return {}
            else:
                print("File upload failed.")
                return {'error': 'Failed to upload the document'}

    except FileNotFoundError:
        print(f"Error: File not found at path: {file_path}")
        return {'error': 'FileNotFoundError: Failed to upload the document'}
    except requests.exceptions.RequestException as e:
        print(f"Error during upload: {e}")
        return {'error': 'RequestException: Failed to upload the document'}
#
def share_pdf_post(cert_metadata, filename, document_id):
    owner_id = "urn:li:organization:" + cert_metadata['linkedin_page_id']
    payload = {
        "author": owner_id,
        "commentary": cert_metadata['post_content'] + cert_metadata['udemy_link'],
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED"
        },
        "content": {
            "media": {
                "title": filename,
                "id": document_id
            }
        },
        "lifecycleState": "PUBLISHED"
    }
    try:
        response = requests.post(LI_REST_URI + 'posts', json=payload, headers=li_headers)

        if response.status_code >= 200 and response.status_code < 300:
            print("The document was shared successfully!")
            return {}
        else:
            print("The document was shared failed.")
            return {'error': 'Failed to share the document'}
    except Exception as e:
        print(e)   
        return {'error': 'Exception: Failed to share the document'}
#
def share_pdf_2_LI(filepath, filename, cert_metadata):
    #1 get upload url
    upload_meta = get_upload_link_document(cert_metadata['linkedin_page_id'])
    if 'error' in upload_meta:
        return upload_meta
    #
    # print(upload_meta)
    upload_url = upload_meta['value']['uploadUrl']
    # print(upload_url)
    upload_result = upload_pdf(filepath, upload_url)
    if 'error' in upload_result:
        return upload_result
    #delay 10 secs to ensure the document is in LI system
    time.sleep(10)
    #create Post to LinkedIn page
    result_share = share_pdf_post(cert_metadata, filename, upload_meta['value']['document'])
    return result_share