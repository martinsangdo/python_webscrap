import requests
import time
#use this class to communicate with LI APIs
class LinkedIn:
    
    def __init__(self, li_uri, li_rest_uri, li_access_token, li_version):
        self.li_uri = li_uri
        self.li_rest_uri = li_rest_uri
        self.li_access_token = li_access_token
        self.li_version = li_version
        self.li_headers = {
            'Authorization': li_access_token,
            'LinkedIn-Version': li_version,
            'X-RestLi-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        }

    #
    def li_get_upload_link_video(self, owner_id, file_size):
        url = self.li_rest_uri + 'videos?action=initializeUpload'
        payload = {
            "initializeUploadRequest": {
                "owner": owner_id,
                "fileSizeBytes": file_size
                # "uploadCaptions": 0,
                # "uploadThumbnail": 0
            }
        }
        try:
            detail = requests.post(url, json=payload, headers=self.li_headers)
            return detail.json()
        except Exception as e:
            print(e)
            return {'error': e}
    #
    def li_upload_video_2_page(self, owner_id, video_path, file_size):
        upload_detail = self.li_get_upload_link_video(owner_id, file_size)
        print(upload_detail)
        uploadUrl = upload_detail['value']['uploadInstructions'][0]['uploadUrl']
        videoId = upload_detail['value']['video']
        try:
            with open(video_path, 'rb') as file:
                files = {'file': (file.name, file, 'video/mp4')}
                headers = {
                    'Content-Type': 'application/octet-stream'
                }

                response = requests.post(uploadUrl, files=files, headers=headers)
                print("Status Code:", response.status_code)
                print("Headers:", response.headers)
                print("Response Body:", response.text)

                if response.status_code >= 200 and response.status_code < 300:
                    print("File uploaded successfully!")
                    time.sleep(5)   #delay 5 seconds for image going through LI system
                    return 'ok', videoId
                else:
                    print("File upload failed.")
                    return 'failed'
        except FileNotFoundError:
            print(f"Error: File not found at path: {video_path}")
            return 'failed' 
        except requests.exceptions.RequestException as e:
            print(f"Error during upload: {e}")
            return 'failed'
    #create a page post to share this video
    def share_video_2_page(self, owner_id, videoId, decription):
        payload = {
            "author": owner_id,
            "commentary": decription,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED"
            },
            "content": {
                "media": {
                    "title": 'Sample questions',
                    "id": videoId
                }
            },
            "lifecycleState": "PUBLISHED"
        }
        try:
            response = requests.post(self.li_rest_uri + 'posts', json=payload, headers=self.li_headers)
            print("Status Code:", response.status_code)
            print("Headers:", response.headers)
            print("Response Body:", response.text)

            if response.status_code >= 200 and response.status_code < 300:
                print("The video was shared successfully!")
                return 'ok'
            else:
                print("The video was shared failed.")
                return 'failed'
        except Exception as e:
            print(e)   
            return 'failed'
    #upload video and share the post
    def upload_and_share_video(self, cert_metadata, question_list, video_path, file_size):
        page_id = cert_metadata['linkedin_page_id']
        page_id = '106416695' #testing
        owner_id = "urn:li:organization:" + page_id
        result_upload, videoId = self.li_upload_video_2_page(owner_id, video_path, file_size)
        if result_upload == 'failed':
            return False
        #share this video to LI
        decription = cert_metadata['name'] + '\n' + '\n'.join(question_list)
        self.share_video_2_page(owner_id, videoId, decription)
