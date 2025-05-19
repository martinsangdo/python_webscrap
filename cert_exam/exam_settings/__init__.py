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
            size=(1920, 1080)
        )
    except Exception as e:
        print(e)
#
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
            font-size: 2em;
        }

        .container {
            padding: 0 200px;
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