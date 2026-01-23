# %%
from dotenv import load_dotenv
import pymongo
import sys
import os
import time
from math import ceil
import csv
import importlib
# Get the current working directory of the notebook
notebook_dir = os.getcwd()
# Get the path to the parent directory
parent_dir = os.path.dirname(notebook_dir)

# Add the parent directory to sys.path if it's not already there
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import const
# importlib.reload(const)

# %%
load_dotenv(override=True) 
GENERATIVE_URI = os.environ['GENERATIVE_URI']
db_client = pymongo.MongoClient(os.environ['DB_URI'])
db = db_client['db_certificates']   
metadata_collection = db['tb_cert_metadata']    #meta data of certificates

# %%
#print(GENERATIVE_URI)

# %%
ROLE_PROMPT = os.environ['ROLE_PROMPT']
COMMON_QUESTION_PROMPT = os.environ['COMMON_QUESTION_PROMPT']
MULTI_CHOICE_PROMPT = COMMON_QUESTION_PROMPT + os.environ['MULTI_CHOICE_PROMPT']
MULTI_SELECTION_PROMPT = COMMON_QUESTION_PROMPT + os.environ['MULTI_SELECTION_PROMPT']

# %%
OPEN_ROUTER_AI_KEY=os.environ['OPENROUTER_KEY']
#platform = 'OPENROUTER'

# %%
def store_questions_2_db(platform, collection, raw_questions, question_type):
    questions = const.extract_questions_from_candidates(platform, raw_questions)
    if questions:
        #parse questions and answers
        question_num = 0
        for q in questions:
            if question_type == 'multiple-choice' or (len(q['answer']) > 1):
                q['exported'] = 0
                q['uuid'] = const.generate_random_uuid()
                #print(q)
                if 'explanation' in q and 'answer' in q and 'question' in q and 'options' in q:
                    if 'A' in q['explanation'] and 'A' in q['options']:
                        const.insert_questions(collection, q)
                        question_num += 1
        print('Stored ' + str(question_num) + ' questions to db successfully')
    else:
        print("Error: No questions found in the parsed content")

# %%
def generate_questions(cert_metadata, platform):
    if 'prompt_context' not in cert_metadata:
        print('Missing prompt_context')
        return
    context = cert_metadata['prompt_context']
    exam_name = cert_metadata['name']

    question_collection = db[cert_metadata['collection_name']]
    exceeded_quota = False
    #multiple choice
    if 'multi_choice_prompt_prefix' in cert_metadata:
        text_prompt = cert_metadata['multi_choice_prompt_prefix'].replace('{exam_name}', exam_name) + MULTI_CHOICE_PROMPT
        final_prompt = ROLE_PROMPT + context + text_prompt
        ################
        # print(final_prompt)
        # return
        ################
        no_of_loop = ceil(cert_metadata['multi_choice_questions'] / 10)
        for i in range(no_of_loop):
            if platform is None or platform == '':
                #default is Gemini
                raw_generated_text = const.post_request_generative_ai(GENERATIVE_URI, final_prompt)
                if 'error' in raw_generated_text and 'message' in raw_generated_text['error']:
                    if raw_generated_text['error']['message'].find('You exceeded your current quota') >= 0:
                        print('You exceeded your current quota, pls try other key or wait until next day')
                        exceeded_quota = True
                        break
            elif platform == 'OPENROUTER':
                raw_generated_text = const.send_raw_request_2_openrouter(final_prompt, OPEN_ROUTER_AI_KEY)
            
            store_questions_2_db(platform, question_collection, raw_generated_text, 'multiple-choice')
            time.sleep(5)   #delay 5 seconds
    #multi selection, if any
    if exceeded_quota == False and 'multi_selection_prompt_prefix' in cert_metadata:
        text_prompt = cert_metadata['multi_selection_prompt_prefix'].replace('{exam_name}', exam_name) + MULTI_SELECTION_PROMPT
        final_prompt = ROLE_PROMPT + context + text_prompt
        no_of_loop = ceil(cert_metadata['multi_selection_questions'] / 10)
        for i in range(no_of_loop):
            raw_generated_text = const.post_request_generative_ai(GENERATIVE_URI, final_prompt)
            if 'error' in raw_generated_text and 'message' in raw_generated_text['error']:
                if raw_generated_text['error']['message'].find('You exceeded your current quota') >= 0:
                    print('You exceeded your current quota, pls try other key or wait until next day')
                    break
            store_questions_2_db(question_collection, raw_generated_text, 'multiple-selection')
            time.sleep(5)   #delay 5 seconds
    

# %%
def begin_generate_questions(cert_symbol, platform, no_of_tests):
    if cert_symbol is None or cert_symbol == '':
        return
    #query metadata of this symbol
    cert_metadata = metadata_collection.find_one({'symbol': cert_symbol})
    if cert_metadata is None:
        print('Certificate not found')
        return
    print('Begin generating questions for: ' + cert_metadata['name'])
    #
    for i in range(no_of_tests):
        generate_questions(cert_metadata, platform)
        print(cert_symbol + ' ========== Finish generating set: ' + str(i+1))

# %%
def export_csv(cert_metadata, test_set_number):
    question_collection = db[cert_metadata['collection_name']]
    file_path = './'+cert_metadata['collection_name']+'/'
    #get questions that not exported yet. Note that: each part must follow by domain percents
    file_data = []
    #append header line (both multi-choice and multi-selection)
    file_data.append(['Question','Question Type','Answer Option 1','Explanation 1','Answer Option 2','Explanation 2','Answer Option 3','Explanation 3','Answer Option 4','Explanation 4','Answer Option 5','Explanation 5','Answer Option 6','Explanation 6','Correct Answers','Overall Explanation','Domain'])
    exported_uuid = []
    manual_uuid = []
    #1. export multiple-choice first
    pipeline = [
                {"$match": {'exported': {"$in": [0, None]}, 'type': 'multiple-choice'}},
                {"$sample": {"size": cert_metadata['multi_choice_questions']}}
            ]
    random_documents = list(question_collection.aggregate(pipeline))
    print('set', test_set_number)
    print('len of questions', len(random_documents))
    for doc in random_documents:
        # print(doc)
        if 'D' not in doc['options']:
            print(doc['options'])
        file_data.append([doc['question'].replace('  ', ' ').replace('\n', ''), 'multiple-choice', 
                                  doc['options']['A'], doc['explanation']['A'].replace('  ', ' ').replace('\n', ''),     #A
                                  doc['options']['B'], doc['explanation']['B'].replace('  ', ' ').replace('\n', ''),     #B
                                  doc['options']['C'], doc['explanation']['C'].replace('  ', ' ').replace('\n', ''),     #C
                                  doc['options']['D'], doc['explanation']['D'].replace('  ', ' ').replace('\n', ''),     #D
                                  '', '',   #E
                                  '', '',   #6
                                  const.map_index(doc['answer']), #correct answer
                                  '', #overall
                                  '' #domain
                                  ])
        exported_uuid.append(doc['_id'])
    #2. multi selection
    if 'multi_selection_questions' in cert_metadata and cert_metadata['multi_selection_questions'] > 0:
        pipeline = [
                    {"$match": {'exported': 0, 'type': 'multiple-selection'}},
                    {"$sample": {"size": cert_metadata['multi_selection_questions']}}
                ]
        random_documents = list(question_collection.aggregate(pipeline))
        for doc in random_documents:
            exported_uuid.append(doc['_id'])
            manual_uuid.append(doc['_id']) #they do not suppor bulk upload this type of question, we need to manually add them
    #save all questions to csv
    filename = cert_metadata['csv_filename_prefix']+test_set_number+'.csv'
    try:
        with open(file_path + filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(file_data)
            print(f"Data successfully saved to '{file_path}{filename}'")
            for _id in exported_uuid:
                question_collection.update_one({'_id': _id}, {'$set': {'exported': 1, 'filename': filename}})
            print('","'.join(manual_uuid))
    except Exception as e:
        print(f"An error occurred while saving the array: {e}")

# %%
#export 1 test at once
def begin_export_csv(cert_symbol, test_set_number):
    if cert_symbol is None or cert_symbol == '':
        return
    cert_metadata = metadata_collection.find_one({'symbol': cert_symbol})
    if cert_metadata is None:
        print('Certificate not found')
        return
    #
    export_csv(cert_metadata, test_set_number)

# %%
#set flag to exams that have incorrect exported test
def find_wrong_exams():
    certs = metadata_collection.find({'udemy_link': {'$ne':None}})
    for cert in certs:
        question_collection = db[cert['collection_name']]
        exported_questions = question_collection.find({'exported': 1})
        if len(list(exported_questions)) < 240:
            print(cert['symbol'])
            print(cert['collection_name'])
            print('========')
#test
# find_wrong_exams()

# %% [markdown]
# 

# %%
#remove duplicated questions by UUID
def remove_duplicated_questions_by_uuid(collection_name):
    question_collection = db[collection_name]
    questions = question_collection.find({})    #find all
    uuid_map = {}   #duplicated uuids, key: uuid, value: 0/1 
    for question in questions:
        if question['uuid'] not in uuid_map:
            #first appear
            uuid_map[question['uuid']] = 1
        else:
            #this UUID is duplicated
            uuid_map[question['uuid']] = uuid_map[question['uuid']] + 1
    #
    for uuid in uuid_map:
        if uuid_map[uuid] > 1:
            #remove duplicated question
            question_collection.delete_many({'uuid':uuid})

#test
#remove_duplicated_questions_by_uuid('tb_az_az_500')

# %%
#remove duplicated questions by question
def remove_duplicated_questions_by_question(collection_name):
    question_collection = db[collection_name]
    questions = question_collection.find({})    #find all
    question_map = {}   #duplicated uuids, key: question, value: 0/1 
    num_of_duplicated = 0
    for question in questions:
        if question['question'] not in question_map:
            #first appear
            question_map[question['question']] = 0
        else:
            #this UUID is duplicated
            question_map[question['question']] = 1
    #
    for question in question_map:
        if question_map[question] > 0:
            num_of_duplicated = num_of_duplicated + 1
    print('num_of_duplicated', num_of_duplicated)
            
    #remove duplicated question
    # for question in question_map:
    #     if question_map[question] > 0:
    #         question_collection.delete_many({'question':question})

#test
remove_duplicated_questions_by_question('tb_itil_foundation')

# %%
#run it: python generate_questions.py
cert_symbol = 'ITIL_FOUNDATION' #predefined in db (create new folder in this project in advance)
platform = ''
# begin_generate_questions(cert_symbol, platform, 2)    #ideally 6 full tests

#generate CSV files
# for i in range(1,7):  
#     begin_export_csv(cert_symbol, str(i))    #Practice set index

# %%



