#https://github.com/vgalin/html2image
from html2image import Html2Image
import subprocess
import os
hti = Html2Image(custom_flags=['--headless=new', '--quiet=True'], size=(1920, 1080))
#https://github.com/vgalin/html2image/issues/177 (size should generated from HTML code)
#landscape style
def generate_image(str_html, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_str=str_html,
            # html_file='sample.html',
            save_as=filename,
            size=(1920, 1080),
        )
        print('Done generating 1 page image')
        return True
    except Exception as e:
        print(e)
        return False

def generate_image_portrait(str_html, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_str=str_html,
            save_as=filename,
            size=(1080, 1920)
        )
        print('Done generating 1 page image')
        return True
    except Exception as e:
        print(e)
        return False

def generate_image_portrait_from_file(html_filename, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_file=html_filename,
            save_as=filename,
            size=(1080, 1920)
        )
        print('Done generating 1 page image')
        return True
    except Exception as e:
        print(e)
        return False
    
def get_cert_metadata(db, cert_symbol):
    meta_collection = db['tb_cert_metadata']
    #get metadata of the certificate
    cert_metadata = meta_collection.find_one({'symbol': cert_symbol})
    return cert_metadata

def query_random_questions(db, num_of_questions, channel, cert_metadata):
    #query random questions
    condition = {'type': 'multiple-choice', 'exported': {'$ne': 1}} #not in test course
    condition[channel] = None   #never posted in this channel
    pipeline = [
                {"$match": condition},
                {"$sample": {"size": num_of_questions}} #randomly documents
            ]
    collection = db[cert_metadata['collection_name']]
    random_documents = list(collection.aggregate(pipeline))
    if len(random_documents) < num_of_questions:
        print('Not enough questions to export')
        return []
    return random_documents

def update_questions_posted(db, cert_metadata, channel, today_yyyymmdd, docs):
    collection = db[cert_metadata['collection_name']]
    for doc in docs:
        #indicate that this question is shared in this channel at this date
        collection.update_one({'uuid': doc['uuid']}, {'$set':{channel: today_yyyymmdd}})


########## 1 page 1 image styles
html_head_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Question and Answers</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            font-family: sans-serif;
            font-size: 3em;
        }

        .container {
            padding: 0 100px;
            text-align: center;
        }

        .container .div_explan {
            font-size: 0.8em;
        }

        .question {
            margin-bottom: 20px;
            line-height: 1.4;
            text-align: left;
            font-weight: bold;
        }

        .answer, .explanation {
            margin-bottom: 15px;
            text-align: left;
        }

        .answer label {
            display: block;
            line-height: 1.4;
            padding: 8px;
        }

        .answer label.correct {
            color: green;
            font-weight: bold;
        }

        .container .div_explan .answer label {
            line-height: 1.0;
        }

        .explanation {
            display: none;
        }

        .explanation label {
            font-size: 0.6em;
            font-style: italic;
        }

        .explanation.show {
            display:block;
        }
    </style>
</head>
<body>
    <div class="container">
'''

html_tail_str = '''
        </div>
    </body>
</html>
'''
########## PDF styles
html_pdf_head_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Question and Answers</title>
    <style>
        @page {
            size: a4;
            @frame content_frame {
                left: 15pt;
                width: 580pt;
                top: 15pt;
                right: auto;
                bottom: auto;
                height: 800pt;
            }
        }

        body {
            display: flex;
            min-height: 100vh;
            margin: 0;
            font-family: sans-serif;
            font-size: 1.2em;
            flex-direction: column;
        }

        .container {
            padding: 20px;
            text-align: center;
        }

        .question {
            text-align: left;
            font-weight: bold;
        }

        .answer, .explanation {
            text-align: left;
        }

        .answer label {
            display: block;
            padding: 2px;
        }

        .answer label.correct {
            color: green;
            font-weight: bold;
        }

        .explanation {
            display: none;
        }

        .explanation label {
            display: block;
            font-style: italic;
            padding: 5px;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .explanation.show {
            display:block;
        }

        .explanation.show .correct{
            color: green;
            font-weight: bold;
        }

        .copyright {
            font-size: 0.5em;
            margin-top:50px;
            bottom: 5px;
        }

        .checkout {
            margin-top:50px;
            bottom: 5px;
            font-size:0.5em;
        }
    </style>
</head>
<body>
'''

html_pdf_tail_str = '''
    </body>
</html>
'''
######### 1 image 6 questions styles
html_head_1_img_6_q_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Question and Answers</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 5px;
            font-family: sans-serif;
            font-size: 2em;
            flex-direction: column;
        }
        .header {margin-bottom:10px;font-size:20px;text-align:center;}

        table tr td {
            padding: 15px;
        }

        .question {
            margin-bottom: 10px;
            line-height: 1.4;
            text-align: left;
            font-weight: bold;
        }

        .answer, .explanation {
            margin-bottom: 5px;
            text-align: left;
        }

        .answer label {
            display: block;
            line-height: 1.4;
            padding: 6px;
        }
        .footer {margin-top:10px;font-size:12px;text-align:center;}
    </style>
</head>
<body>
'''

html_tail_1_img_6_q_str = '''
        </body>
</html>
'''
######### image with 3 questions
html_head_1_img_3_q_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Question and Answers</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            font-family: sans-serif;
            font-size: 1.6em;
            flex-direction: column;
        }

        .header {
            margin-top:20px;
            text-align: center;
            font-weight: bold;
            font-size: 2em;
        }

        .container {
            padding: 40px;
            text-align: center;
        }

        .question {
            margin-bottom: 20px;
            line-height: 1.4;
            text-align: left;
            font-weight: bold;
        }

        .answer {
            margin-bottom: 5px;
            text-align: left;
        }

        .answer label {
            display: block;
            line-height: 1.4;
            padding: 8px;
        }

        .footer {
            margin-top:20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
'''

html_tail_1_img_3_q_str = '''
        <div class="header">---</div>
        <div class="footer">Discover more <strong>questions</strong> and <strong>certificates</strong> via this link: <a href="https://sites.google.com/view/tech-certificates">https://sites.google.com/view/tech-certificates</a></div>
    </body>
</html>
'''
##########
def index_to_string(index):
  if 1 <= index <= 20:
    return f"{index:02d}"
  else:
    return ""
#1 image 1 question
def generate_images(today_yyyymmdd, cert_metadata, documents):
    index = 1
    for doc in documents:
        str_index = str(index) + ') '
        #question first
        html_question = '<div class="question">'+str_index + doc['question']+'</div>'
        html_answers_start = '<div class="answers">'
        html_answers_end = '</div>'
        #First images: options without explanations
        for key in doc['options'].keys():
            html_answers_start += f'''
                <div class="answer">
                    <label>{key}. {doc['options'][key]}</label>
                </div>
                <div class="explanation">
                    <label>{key}. {doc['explanation'][key]}</label>
                </div>'''
        #1 doc 1 image
        exported_result = generate_image(html_head_str + html_question + html_answers_start + html_answers_end + html_tail_str, cert_metadata['img_folder_path']+"/"+today_yyyymmdd, index_to_string(index) + '.png')
        if exported_result == False:
            break   #something wrong with this image
        #Second images: options with explanations
        html_answers_start = '<div class="answers">'
        for key in doc['options'].keys():
            correct_class = ''
            if doc['answer'] == key:
                correct_class = ' correct'
            html_answers_start += f'''
                <div class="answer">
                    <label class="{correct_class}">{key}. {doc['options'][key]}</label>
                </div>
                <div class="explanation show">
                    <label>{doc['explanation'][key]}</label>
                </div>'''
        exported_result = generate_image(html_head_str + '<div class="div_explan">' + html_question + html_answers_start + html_answers_end + '</div>' + html_tail_str, cert_metadata['img_folder_path']+"/"+today_yyyymmdd, '_'+index_to_string(index) + '.png')
        if exported_result == False:
            break   #something wrong with this image
        #
        index += 1
    print(index)
    if index == len(documents) + 1:
        return True #all images are exported successfully
    return False    #one of image is not exported well
####
def generate_1_img_multiple_questions(random_documents, cert_metadata, today_yyyymmdd):
    question_index = 1
    document_html = []
    document_html.append(html_head_1_img_3_q_str)
    #1. add header
    document_html.append('<div class="header">'+cert_metadata['name']+'</div>')
    #2. add questions
    for doc in random_documents:
        container_html = []
        container_html.append('<div class="container">')
        str_index = str(question_index) + ') '
        #question first
        container_html.append('<div class="question">'+str_index + doc['question']+'</div>')
        #2.1 add answers
        container_html.append('<div class="answers">')
        for key in doc['options'].keys():
            container_html.append( f'''
                    <div class="answer">
                        <label>{key}. {doc['options'][key]}</label>
                    </div>''')
        container_html.append('</div>') #end list of answers
        container_html.append('</div>') #end 1 container
        document_html.append(''.join(container_html))
        question_index += 1
    #add footer (optional because image/video cannot click on the link)
    # document_html.append('<div class="footer">Check out more questions via <a href="'+cert_metadata['udemy_link']+'">this link</a></div>')
    #end doc
    document_html.append(html_tail_1_img_3_q_str)
    #1 doc 1 image
    filename = 'img_multi_q_'+today_yyyymmdd + '.png'
    creation_result = generate_image_portrait(''.join(document_html), cert_metadata['img_m_q_folder_path'], filename)
    return creation_result, filename
#
def create_video_from_images(ffmpeg_path, image_folder, output_filename, framerate, image_name_pattern):
    """
    Creates a video from all JPG images in a specified folder using ffmpeg.

    Args:
        image_folder (str): The path to the folder containing the images.
        output_filename (str): The name of the output video file.
        framerate (int): The framerate of the output video (frames per second).
    """
    # Ensure image_folder is an absolute path for better reliability
    abs_image_folder = os.path.abspath(image_folder)
    
    # Define the output path. It's often good to save the output in the same folder of images
    abs_output_path = os.path.abspath(image_folder + "/" + output_filename)

    # Construct the ffmpeg command.
    # We pass the full command as a list of strings.
    # The -y flag will automatically overwrite the output file if it exists.
    #ffmpeg -framerate 1/30 -i %02d.png -c:v libx264 -r 25 -pix_fmt yuv420p output.mp4
    ffmpeg_command = [
        ffmpeg_path,
        "-framerate", framerate,
        "-i", abs_image_folder + image_name_pattern,
        # "-frames:v", "20",
        #"-pattern_type", "glob",
        # "-i", "*.png",  # This will look for *.jpg inside the 'cwd' (image_folder)
        # "-f", "concat",
        # "-safe", "0",
        # "-i", "/Users/sang/Documents/Source/Python/python_webscrap/cert_exam/aws_sa_data/img_youtube/20250521/video_duration.txt",
        "-c:v", "libx264",
        "-r", "25",
        "-pix_fmt", "yuv420p",
        "-y", # Overwrite output file without asking
        # Note: We don't specify the full output path here directly
        # because the command is run from the 'image_folder'.
        # Instead, we pass the absolute path relative to the script's original location.
        abs_output_path
    ]

    print(f"Attempting to create video from images in: {abs_image_folder}")
    print(f"Output video will be: {abs_output_path}")
    print(f"FFmpeg command: {' '.join(ffmpeg_command)}")

    try:
        # Use subprocess.run() to execute the command.
        # cwd: Changes the current working directory for the command execution.
        #      This is key to making "*.jpg" work correctly.
        # check=True: Raises an exception if the command returns a non-zero exit code (i.e., fails).
        # capture_output=True: Captures stdout and stderr.
        # text=True: Decodes stdout and stderr as text.
        result = subprocess.run(
            ffmpeg_command,
            cwd=abs_image_folder, # This changes the directory for THIS command execution
            check=True,
            capture_output=True,
            text=True
        )
        print("\nFFmpeg command executed successfully!")
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr) # ffmpeg often prints progress to stderr
        print(f"Video '{output_filename}' created successfully at {abs_output_path}")
        return True
    except FileNotFoundError:
        print(f"Error: FFmpeg command not found. Make sure FFmpeg is installed and in your system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg command failed with exit code {e.returncode}")
        print("STDOUT:")
        print(e.stdout)
        print("STDERR:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False