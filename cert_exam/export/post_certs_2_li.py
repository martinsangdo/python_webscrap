# %% [markdown]
# # Auto post to Social site
# Schedule: 1 Image post per day per Page (setup n cron items, each item has 1 category in param)

# %%
from PIL import Image, ImageDraw, ImageFont
import pymongo
import os
import requests
import time
from datetime import datetime
import random

# %%
from dotenv import load_dotenv
load_dotenv(override=True) 
LI_URI = os.environ['LI_URI']
LI_REST_URI = os.environ['LI_REST_URI']
LI_VERSION = os.environ['LI_VERSION']

# %%
db_client = pymongo.MongoClient(os.environ['REMOTE_MONGO_DB'])
db = db_client['db_certificates']   
tb_advertising_posts = db['tb_advertising_posts']   #store contents to post in social media
tb_cert_metadata = db['tb_cert_metadata']    #meta data of certificates
tb_linkedin_app = db['tb_linkedin_app']    #LI App
tb_linkedin_page = db['tb_linkedin_page']    #LI Page info

# %%
def get_timestamp():
    return str(int(time.time()))

def wrap_text(text, font, max_width, draw):
    """
    Splits text into lines that fit within max_width
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        w = draw.textlength(test_line, font=font)

        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

def draw_wrapped_text(draw, position, text, font, max_width, fill=(255,255,255), line_spacing=6):
    x, y = position
    lines = wrap_text(text, font, max_width, draw)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_spacing


# %%
#current path of this project
CURRENT_PATH = '/Users/sangdo/Documents/Source/Python/python_webscrap/cert_exam/'

# %%
CTA_LINKS = '\nVisit the links above to help you pass these certifications at your first try\n'

# %%
#define 5 carousel templates
CAROUSEL_TEMPLATE_POSITION_MAPPING = [
    #carousel 1
    {
        'folder_name': 'carousel_1',
        'header_font_size': 50,
        'content_font_size': 40,
        'position_mapping': [
            #slide 1: hook
            {
                "header": (60, 285)
            },
            #slide 2: problems
            {
                "header": (115, 390),
                "content": (115, 680)
            },
            #slide 3: insight
            {
                "header": (115, 390),
                "content": (115, 680)
            },
            #slide 4: values
            {
                "header": (115, 390),
                "content": (115, 680)
            },
            #slide 5: logo
            {
                "link": (53, 100),
                "link_w": 980,
                "logo": [(53, 290), (53, 630), (53, 975)], #list of positions of each logo
                "title": [(370, 290), (370, 630), (370, 975)], #list of positions of each logo
                "title_w": 700,
                "salary": [(370, 535), (370, 880), (370, 1210)] #list of positions of each logo
            }
        ]
    }
]

# %%
# IMAGE_TEMPLATE_MAPPING = [
#     {  #template 1 (1.png)
#         'template_filename': '1.png',
#         'header_font_size': 50,     #for salary and header
#         'content_font_size': 40,
#         'max_text_w': 1015,
#         'position_mapping': {
#             'salary': (255, 30),
#             'hook': (30, 130),
#             'sub_content_l': 30,
#             'sub_content_t': 355,
#             'logos': [(30, 730), (370, 730), (745, 730)]
#         }
#     },
#     {  #template 2
#         'template_filename': '2.png',
#         'header_font_size': 50,     #for salary and header
#         'content_font_size': 40,
#         'max_text_w': 1015,
#         'position_mapping': {
#             'salary': (255, 30),
#             'hook': (30, 130),
#             'sub_content_l': 30,
#             'sub_content_t': 355,
#             'logos': [(30, 730), (370, 730), (745, 730)]
#         }
#     }
# ]

# %%
TEMPLATE_GROUP = {  #key: template filename, value: group id
    '1.png': 'group_1', 
    '2.png': 'group_1', 
    '3.png': 'group_1', 
    '4.png': 'group_1', 
    '5.png': 'group_1',   #from 1 to 5
    '6.png': 'group_2',
    '7.png': 'group_3',
    '8.png': 'group_4',
    '9.png': 'group_5',
    '10.png': 'group_5',
}

# %%
#2 or 3 certifications in 1 image
LOGO_POSITIONS = [(70, 290), (70, 630), (70, 985)]
NAME_POSITIONS = [(410, 350), (410, 695), (410, 1035)]  #certs name
SALARY_POSITION = (200, 130)    #salary range
FOOTER_URL_POSITION = (330, 1305)   #https://udemy/...

SINGLE_IMG_TEMPLATE_PATH = CURRENT_PATH + 'template/imgs/'

IMG_TEMPLATE_PATH = CURRENT_PATH + 'template/img_template.png'
IMG_LOGO_PATH_PREFIX = CURRENT_PATH + 'logo/'

IMG_OUTPUT_PATH_PREFIX = CURRENT_PATH + 'output/'  #the final image
FONT_PATH = CURRENT_PATH + "font/Inter.ttf"

# %%


# %%
IMAGE_TEMPLATE_INFO = {
    'group_1': {
        'font_name': '',
        'header_font_size': 50,     #for salary and header
        'content_font_size': 40,
        'max_text_w': 1015,
        'sub_content_font_size': 40,
        'salary_font_size': 50,
        'position_mapping': {
                'salary': (255, 30),
                'hook': (30, 135),
                'sub_content_l': 30,
                'sub_content_t': 355,
                'logos': [(30, 730), (370, 730), (745, 730)]
        }
    },
    'group_2': {
        'font_name': '',
        'header_font_size': 50,
        'content_font_size': 40,
        'max_text_w': 1005,
        'sub_content_font_size': 30,
        'salary_font_size': 40,
        'position_mapping': {
                'salary': (60, 1000),
                'hook': (35, 395),
                'sub_content_l': 50,
                'sub_content_t': 630,
                'logos': [(30, 35), (370, 35), (745, 35)]
        }
    },
    'group_3': {
        'font_name': '',
        'header_font_size': 50,
        'content_font_size': 40,
        'max_text_w': 1005,
        'sub_content_font_size': 30,
        'salary_font_size': 30,
        'position_mapping': {
                'salary': (590, 25),
                'hook': (35, 80),
                'sub_content_l': 30,
                'sub_content_t': 330,
                'logos': [(30, 700), (370, 700), (745, 700)]
        }
    },
    'group_4': {
        'font_name': '',
        'header_font_size': 50,
        'content_font_size': 40,
        'max_text_w': 1005,
        'sub_content_font_size': 30,
        'salary_font_size': 40,
        'position_mapping': {
                'salary': (620, 50),
                'hook': (30, 140),
                'sub_content_l': 30,
                'sub_content_t': 370,
                'logos': [(30, 730), (370, 730), (745, 730)]
        }
    },
    'group_5': {
        'font_name': '',
        'header_font_size': 50,
        'content_font_size': 40,
        'max_text_w': 1005,
        'sub_content_font_size': 30,
        'salary_font_size': 35,
        'position_mapping': {
                'salary': (660, 25),
                'hook': (30, 95),
                'sub_content_l': 30,
                'sub_content_t': 330,
                'logos': [(30, 720), (370, 720), (745, 720)]
        }
    }
}

#output: 1 image with multiple certifications from single image template
def create_certifications_from_single_image_template(
    template_filename,
    template_info,
    post_info,
    output_filename
):
    base = Image.open(SINGLE_IMG_TEMPLATE_PATH + template_filename).convert("RGBA")
    draw = ImageDraw.Draw(base)
    #draw salary range
    draw_wrapped_text(
        draw=draw,
        position= template_info['position_mapping']['salary'],
        text= 'Salary: ' + post_info['salary'],
        font= ImageFont.truetype(FONT_PATH, template_info['salary_font_size']),
        max_width= 575,
        fill= (255, 255, 255)   #text color
    )
    #draw hook
    draw_wrapped_text(
        draw=draw,
        position= template_info['position_mapping']['hook'],
        text= post_info['hook'].upper(),
        font= ImageFont.truetype(FONT_PATH, 50),
        max_width= template_info['max_text_w'],
        fill= (0, 0, 0)   #text color
    )
    #draw sub contents
    index = 0
    for sub_content in post_info['sub_contents']:
        draw_wrapped_text(
            draw=draw,
            position= (template_info['position_mapping']['sub_content_l'], template_info['position_mapping']['sub_content_t'] + index * 125),
            text= sub_content,
            font= ImageFont.truetype(FONT_PATH, template_info['sub_content_font_size']),
            max_width= template_info['max_text_w'],
            fill= (0, 0, 0)   #text color
        )
        index = index + 1
    #draw logos
    index = 0
    for symbol in post_info['symbols']:
        overlay_img = Image.open(IMG_LOGO_PATH_PREFIX + symbol + '.png').convert("RGBA")
        base.paste(overlay_img, template_info['position_mapping']['logos'][index], overlay_img)
        index = index + 1

    base.convert("RGB").save(IMG_OUTPUT_PATH_PREFIX + output_filename, "PNG")
    print(f"Final image saved to: {IMG_OUTPUT_PATH_PREFIX}")
    #print link for each cert
    symbol_link_map = {}
    for symbol in post_info['symbols']:
        cert_details = tb_cert_metadata.find_one({'symbol':symbol})
        # print(cert_details['name'])
        #landing page
        link = 'https://certification-pro.blogspot.com/2026/02/' + cert_details['slug'] + '.html'
        # print(link)
        symbol_link_map[symbol] = link
    return symbol_link_map

#test
tb_advertising_posts = db['tb_advertising_posts']
post_details = tb_advertising_posts.find_one({'posted': 0, 'category': 'AI'})
template_filename = '10.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
# create_certifications_from_single_image_template(template_filename, template_info, post_details, 'AI_20260219.png')

# %%
#show link of all certifications
def show_landing_url():
    all_certs = tb_cert_metadata.find({'slug':{'$in':[
        "isaca-certified-information-security-manager-cism",
    ]}})
    for cert in all_certs:
        print(cert['name'])
        print(cert['slug'])
        print('https://certification-pro.blogspot.com/2026/02/' + cert['slug'] + '.html')

#test
# show_landing_url()


# %%
#find a daily post
def export_daily_post(_category):
    tb_advertising_posts = db['tb_advertising_posts']
    post = tb_advertising_posts.find_one({'posted': 0, 'category': _category})
    if post is not None:
        create_certifications_from_single_image_template(post)
#test
# export_daily_post('AI')

# %%
#output: 1 image with multiple certifications in slide
def create_certifications_image(
    page_link:str,
    cert_symbols: list,
    cert_names: list,
    salary_range: str,
    output_path: str
):
    base = Image.open(IMG_TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(base)
    index = 0
    # ---- Add logo images ----
    for symbol in cert_symbols:
        overlay_img = Image.open(IMG_LOGO_PATH_PREFIX + symbol + '.png').convert("RGBA")
        #don't need to resize because logos are saved with size 330x330
        # if "size" in item and item["size"]:
        #     overlay_img = overlay_img.resize(item["size"], Image.ANTIALIAS)
        base.paste(overlay_img, LOGO_POSITIONS[index], overlay_img)
        index = index + 1

    # ---- Add certification names ----
    index = 0
    for t in cert_names:
        font = ImageFont.truetype(FONT_PATH, 48)
        draw_wrapped_text(
            draw=draw,
            position= NAME_POSITIONS[index],
            text= t,
            font= font,
            max_width= 620,
            fill= (0, 0, 153),   #certification name color
            line_spacing=8
        )
        index = index + 1
    #draw salary range
    draw_wrapped_text(
            draw=draw,
            position= SALARY_POSITION,
            text= 'Salary range: ' + salary_range,
            font= ImageFont.truetype(FONT_PATH, 60),
            max_width= 800,
            fill= (153, 153, 0)   #text color
        )
    #draw footer
    draw_wrapped_text(
            draw=draw,
            position= FOOTER_URL_POSITION,
            text= page_link,
            font= ImageFont.truetype(FONT_PATH, 20),
            max_width= 620,
            fill= (0, 0, 255)
        )

    base.convert("RGB").save(output_path, "PNG")
    print(f"Final image saved to: {output_path}")


# %%
#share new post with 1 new uploaded image
def share_my_img_2_LI(asset, owner_id, access_token, post_content):
    #print('asset: ' + asset)
    payload = {
        "author": owner_id,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_content
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    li_headers = {
        'Authorization': access_token,
        'LinkedIn-Version': LI_VERSION,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(LI_URI + 'v2/ugcPosts', json=payload, headers=li_headers)
        # print('====== Share Post to Page results:')
        # print("Status Code:", response.status_code)
        # print("Headers:", response.headers)
        # print("Response Body:", response.text)
        
        if response.status_code >= 200 and response.status_code < 300:
            print("The image was shared successfully!")
            return 'ok'
        else:
            print("The image was shared failed.")
            return 'failed'
    except Exception as e:
        print(e)   
        return 'failed'

# %%
#upload image to LI
def upload_img_2_LI_and_share(li_access_token, file_path, upload_detail, owner_id, post_content):
    uploadUrl = upload_detail['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    #upload the image https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin#upload-image-or-video-binary-file
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (file.name, file, 'image/jpg')}
            headers = {
                'Authorization': li_access_token,
                'LinkedIn-Version': LI_VERSION
            }

            response = requests.post(uploadUrl, files=files, headers=headers)
            # print('====== Upload image results:')
            # print("Status Code:", response.status_code)
            # print("Headers:", response.headers)
            # print("Response Body:", response.text)

            if response.status_code >= 200 and response.status_code < 300:
                print("File uploaded successfully!")
                time.sleep(5)   #delay 5 seconds for image going through LI system
                result = share_my_img_2_LI(upload_detail['asset'], owner_id, li_access_token, post_content)
                return result
            else:
                print("File upload failed.")
                return 'failed'

    except FileNotFoundError:
        print(f"Error: File not found at path: {file_path}")
        return 'failed' 
    except requests.exceptions.RequestException as e:
        print(f"Error during upload: {e}")
        return 'failed'
    

# %%
#get upload link from LI
def get_LI_upload_link(owner_id, li_headers):
    url = LI_URI + 'v2/assets?action=registerUpload'
    payload = {
        "registerUploadRequest": {
            "recipes": [
                "urn:li:digitalmediaRecipe:feedshare-image"
            ],
            "owner": owner_id,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    try:
        detail = requests.post(url, json=payload, headers=li_headers)
        return detail.json()
    except Exception as e:
        print(e)
        return {'error': e}

# %%
def today_as_yyyymmdd():
    return datetime.today().strftime("%Y%m%d")

def get_rand():
    return random.randint(1, 10)

# %%
def post_1_image_by_category(_category, template_filename, template_info):
    tb_advertising_posts = db['tb_advertising_posts']
    post_details = tb_advertising_posts.find_one({'posted': 0, 'category': _category})
    if post_details is None:
        print('There is no post for Image content of category: ' + _category)
        return
    if 'symbols' not in post_details:
        print('There is no symbol for Image content of category: ' + _category)
        return
    #create image with current datetime
    output_filename = _category + '_' + today_as_yyyymmdd() + '.png'
    symbol_link_map = create_certifications_from_single_image_template(template_filename, template_info, post_details, output_filename)
    # print(symbol_link_map)
    if not symbol_link_map:
        print('Cannot get links for category: ' + _category)
        return
    #find app token and page linking to this category
    page_info = tb_linkedin_page.find_one({'category': _category})
    if page_info is None:
        print('There is no page info for category: ' + _category)
        return
    #find LI app info
    app_info = tb_linkedin_app.find_one({'app_id': page_info['app_id']})
    if app_info is None:
        print('There is no app info for category: ' + _category)
        return
    post_content = post_details['content'] + CTA_LINKS
    #replace with links
    for symbol, link in symbol_link_map.items():
        post_content = post_content.replace('{'+symbol+'}', link)
    #upload image to to Linkedin Page
    li_access_token = 'Bearer ' + app_info['access_token']
    li_headers = {
        'Authorization': li_access_token,
        'LinkedIn-Version': LI_VERSION,
        'Content-Type': 'application/json'
    }
    owner_id = "urn:li:organization:" + page_info['page_id']    #my page
    upload_link = get_LI_upload_link(owner_id, li_headers)
    new_img_path = IMG_OUTPUT_PATH_PREFIX + output_filename
    result_upload = upload_img_2_LI_and_share(li_access_token, new_img_path, upload_link['value'], owner_id, post_content)
    if result_upload == 'ok':
        #the post is successfully up
        #delete that image
        # if os.path.exists(new_img_path):  #keep for auditing
        #     os.remove(new_img_path)
        print('==== The image is shared in LI Page for category: ' + _category)
        print(page_info['link']) #page link
        #add flag to that post to indicate done
        post_details['posted'] = 1
        tb_advertising_posts.replace_one({"_id": post_details['_id']}, post_details)
        #remove the image
        os.remove(new_img_path)
        return
    else:
        print('There is an error for posting in LI page for category: ' + _category)
        return
#post to LinkedIn page
template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('GENERAL', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('AI', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('PROJECT_MANAGEMENT', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('AGILE', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('CLOUD', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('DATA_ENGINEER', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('SOLUTIONS_ARCHITECT', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('DIGITAL_INTELLIGENCE', template_filename, template_info)

template_filename = str(get_rand()) + '.png'
template_info = IMAGE_TEMPLATE_INFO[TEMPLATE_GROUP[template_filename]]
post_1_image_by_category('SECURITY', template_filename, template_info)


# %%
# if __name__ == '__main__':
#     args = sys.argv
#     print(args)
#     if len(args) > 1:
#         category = args[1]   #category of certifications
#         print(category)
#         post_1_image_by_category(category)

# %%
db_client.close()


