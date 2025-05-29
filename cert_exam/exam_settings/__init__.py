#https://github.com/vgalin/html2image
from html2image import Html2Image

hti = Html2Image(custom_flags=['--headless=new', '--quiet=True'], size=(1920, 1080))
#https://github.com/vgalin/html2image/issues/177 (size should generated from HTML code)

def generate_image(str_html, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_str=str_html,
            # html_file='sample.html',
            save_as=filename,
            size=(1920, 1080),
        )
    except Exception as e:
        print(e)

def generate_image_portrait(str_html, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_str=str_html,
            save_as=filename,
            size=(1080, 1920)
        )
    except Exception as e:
        print(e)

def generate_image_portrait_from_file(html_filename, folder_path, filename):
    hti.output_path = folder_path
    try:
        hti.screenshot(
            html_file=html_filename,
            save_as=filename,
            size=(1080, 1920)
        )
    except Exception as e:
        print(e)
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

        .explanation {
            display: none;
        }

        .explanation label {
            font-size: 0.7em;
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