'''
this file will show all the models, including custom builds with their model_id that are stored in the Document Intelligence service
'''
import os
from dotenv import find_dotenv, load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceAdministrationClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv(find_dotenv())
endpoint = os.environ.get("DOCUMENTINTELLIGENCE_ENDPOINT")
key = os.environ.get("DOCUMENTINTELLIGENCE_API_KEY")

# Create DocumentIntelligenceClient
client = DocumentIntelligenceAdministrationClient(endpoint=endpoint, credential=AzureKeyCredential(key))

models = client.list_models()

for model in models:
    print(f"Model ID: {model.model_id}")
