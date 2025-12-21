from flask import Flask, request, jsonify
from dotenv import load_dotenv
import pymongo
import os

load_dotenv(override=True) 
db_client = pymongo.MongoClient(os.environ['DB_URI'])
db = db_client['db_certificates'] 


question_collection = db['tb_docker_dca']    ##### HARD CODE 


# Initialize the Flask application
app = Flask(__name__)

# Define a route for the root URL
@app.route('/')
def home():
    return "<h1>Hello, Flask!</h1><p>Welcome to your first Python web app.</p>"

@app.route('/import_question', methods=['POST'])
def import_question():
    data = request.get_json()
    if not data or 'questions' not in data:
        return jsonify({
            "error": "Invalid request",
            "message": "Please provide 'questions' in the JSON body."
        }), 400

    questions = data['questions']  #list of question
    no_of_invalid_questions = 0
    no_of_valid_questions = 0
    #validate question
    for raw_question in questions:
        if 'explanation' not in raw_question:
            no_of_invalid_questions = no_of_invalid_questions + 1
            continue
        if 'A' not in raw_question['explanation']:
            no_of_invalid_questions = no_of_invalid_questions + 1
            continue
        #check duplicated of question content
        raw_question_string = raw_question['question']
        doc_existed = question_collection.find_one({'question':raw_question_string})
        if doc_existed is not None:
            #duplicated question
            no_of_invalid_questions = no_of_invalid_questions + 1
            continue
        #insert into db
        question_collection.insert_one(raw_question)
        no_of_valid_questions = no_of_valid_questions + 1

    # 4. Return a success response
    return jsonify({
        "message": "Question imported successfully",
        "no_of_invalid_questions": no_of_invalid_questions,
        "no_of_valid_questions": no_of_valid_questions
    }), 201

# Run the app if this script is executed
if __name__ == '__main__':
    app.run(debug=True)