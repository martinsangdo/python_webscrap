import uuid
import time
import requests
import re
import json
from datetime import datetime

#constant
PART='contentDetails,snippet'
PER_PAGE='10'
REQUEST_HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0'}
#database
# ln -s /Applications/MAMP/tmp/mysql/mysql.sock /tmp/mysql.sock
HOSTNAME = 'localhost'
USERNAME = 'root'
PASSWORD = 'root'
DATABASE = 'gameletgo'

TOP_COIN_NEWS_CAT_ID = 615

#
def generate_random_uuid():
    """Generates a random UUID (Universally Unique Identifier).

    Returns:
        A string representing the UUID.
    """
    return str(uuid.uuid4())
#
def get_current_timestamp_milliseconds():
  """
  Returns the current timestamp in milliseconds since the epoch.
  """
  return int(time.time() * 1000)

#Send a POST request to generative host
def post_request_generative_ai(GENERATIVE_URI, text_prompt):
    HEADER = {'Content-Type': 'application/json'}
    json_data = {
        "contents": [
            { "parts": [
                {"text": text_prompt}]
            }
        ]
    }

    try:
        r = requests.post(GENERATIVE_URI, headers=HEADER, json=json_data)
        return r.json()
    except Exception as e:
       print(e)
       return {'error': e}
#map A - E to 1 - 5
def map_index(a_char):
    if a_char == 'A':
        return 1
    if a_char == 'B':
        return 2
    if a_char == 'C':
        return 3
    if a_char == 'D':
        return 4
    if a_char == 'E':
        return 5
def parse_candidate_content(data):
    """
    Parses the content from a dictionary in the 'candidates' list.
    Specifically looks for JSON content within the 'text' part
    and attempts to load it.

    Args:
        data (dict): A dictionary representing an item in the 'candidates' list.

    Returns:
        dict or str or None: If JSON content is found and successfully
                             parsed, it returns the parsed dictionary.
                             If no JSON is found, it returns the raw text.
                             Returns None if the expected structure is not found.
    """
    if not isinstance(data, dict) or 'content' not in data or not isinstance(data['content'], dict) or 'parts' not in data['content'] or not isinstance(data['content']['parts'], list):
        return None

    for part in data['content']['parts']:
        if isinstance(part, dict) and 'text' in part:
            text_content = part['text'].strip()
            # Use regex to find JSON blocks within the text
            json_match = re.search(r'```json\n(.*?)\n```', text_content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    return text_content  # Return the raw text in case of an error
            elif text_content:
                return text_content  # Return the raw text if no JSON block is found

    return None

def extract_questions_from_candidates(response_data):
    """
    Extracts and parses the 'questions' list from the 'candidates'
    in the given response data.

    Args:
        response_data (dict): The dictionary containing the response data.

    Returns:
        list or None: A list of question dictionaries if found and parsed,
                     otherwise None.
    """
    if not isinstance(response_data, dict) or 'candidates' not in response_data or not isinstance(response_data['candidates'], list):
        return None

    for candidate in response_data['candidates']:
        parsed_content = parse_candidate_content(candidate)
        if isinstance(parsed_content, dict) and 'questions' in parsed_content and isinstance(parsed_content['questions'], list):
            return parsed_content['questions']

    return None

# Example usage with your provided data:
#response_data = {'candidates': [{'content': {'parts': [{'text': '```json\n{\n  "questions": [\n    {\n      "question": "Your company is launching a new e-commerce platform on AWS.  The platform will handle sensitive customer data, including credit card information and personally identifiable information (PII). You need to design a secure architecture that meets PCI DSS compliance requirements.  Describe a comprehensive approach to securing the application, covering data at rest, data in transit, and access control. Consider the use of specific AWS services and explain your rationale for choosing them.  Focus on practical implementation details rather than just naming services.",\n      "topics": ["Data Security", "PCI DSS Compliance", "IAM", "KMS", "VPC", "Security Groups", "WAF", "S3", "Encryption"],\n      "difficulty": "Hard"\n    },\n    {\n      "question": "A client has an existing on-premises application that needs to be migrated to AWS. The application interacts with a legacy database that contains highly sensitive customer records. During the migration, you must ensure that the database remains secure and complies with data sovereignty regulations for Europe (GDPR).  How would you design the migration strategy to minimize downtime and maintain security throughout the process?  Be specific about your choices of AWS services and how you will address data encryption, network security, and compliance.  Consider potential challenges and mitigation strategies.",\n      "topics": ["Data Sovereignty", "GDPR", "Database Migration", "VPN", "Direct Connect", "RDS", "Database Encryption", "IAM Roles", "Network Security", "Disaster Recovery"],\n      "difficulty": "Medium"\n    }\n  ]\n}\n```\n'}], 'role': 'model'}, 'finishReason': 'STOP', 'avgLogprobs': -0.3347730217091848}], 'usageMetadata': {'promptTokenCount': 55, 'candidatesTokenCount': 341, 'totalTokenCount': 396, 'promptTokensDetails': [{'modality': 'TEXT', 'tokenCount': 55}], 'candidatesTokensDetails': [{'modality': 'TEXT', 'tokenCount': 341}]}, 'modelVersion': 'xxx'}
#insert questions to collection
def insert_questions(collection, json_question):
    if 'question' in json_question:
        existed_doc = collection.find_one({'question': json_question['question']})
        if existed_doc == None:
            #insert new document
            collection.insert_one(json_question)
            #print('Inserted new doc')

def get_current_date_yyyymmdd():
  """
  Returns the current date as a string in the format yyyymmdd.
  """
  now = datetime.now()
  return now.strftime("%Y%m%d")