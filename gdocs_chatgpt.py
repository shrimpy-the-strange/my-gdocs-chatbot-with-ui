
# Install necessary packages
!pip install flask
from flask import Flask, request, render_template
from llama_index import GPTVectorStoreIndex, download_loader, StorageContext, load_index_from_storage, LLMPredictor, PromptHelper
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from llama_index import GPTVectorStoreIndex, download_loader, StorageContext, load_index_from_storage, LLMPredictor, PromptHelper

# Install ngrok
!pip install pyngrok
import getpass
from pyngrok import ngrok, conf

# Follow the steps here: https://thinkinfi.com/flask-adding-html-and-css/#:~:text=Flask%20allows%20us%20to%20integrate,template%20for%20your%20web%20page to add HTML and CSS in your Flask web application
# Configure Flask app
app = Flask(__name__, template_folder='template-folder-path', static_folder='static-folder-path')
index = None
query_engine = None

# Authorize access to Google Docs
def authorize_gdocs():
    google_oauth2_scopes = [
        "https://www.googleapis.com/auth/documents.readonly"
    ]

    cred = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", google_oauth2_scopes)
            cred = flow.run_local_server(port=0)

        with open("token.pickle", 'wb') as token:
            pickle.dump(cred, token)
            
GoogleDocsReader = download_loader('GoogleDocsReader')

# Specify Google OAuth2 scopes
SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Specify Google Document(s) ID(s)
gdoc_ids = ['google-doc-id-1',
            'google-doc-id-2']

# Run the chatbot
def initialize_chatbot():
    global index, query_engine
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key"

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

        # Subclass GoogleDocsReader to accept custom credentials
    class CustomGoogleDocsReader(GoogleDocsReader):
        def __init__(self, credentials):
            self._credentials = credentials

        def _get_credentials(self):
            return self._credentials

    # Instantiate the CustomGoogleDocsReader with the refreshed credentials
    loader = CustomGoogleDocsReader(credentials=creds)

    # Load documents
    documents = loader.load_data(document_ids=gdoc_ids)

    # Build index
    index = GPTVectorStoreIndex.from_documents(documents)

    # Persist index
    persist_dir = "your-directory-path"  # Specify your directory here
    index.storage_context.persist(persist_dir=persist_dir)

    # Rebuild storage context and load index
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)

    # Initialize query engine
    query_engine = index.as_query_engine()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    prompt = request.form['prompt']
    response = query_engine.query(prompt)
    return render_template('home.html', prompt=prompt, response=response)

if __name__ == '__main__':
    initialize_chatbot()

    # Set up ngrok
    public_url = ngrok.connect(5001)
    print(f"Public URL: {public_url}")
    
    app.run(host='0.0.0.0', port=5001)