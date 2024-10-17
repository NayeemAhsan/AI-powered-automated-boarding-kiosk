import os
import uuid
from dotenv import find_dotenv, load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceAdministrationClient
from azure.ai.documentintelligence.models import (
        DocumentBuildMode,
        BuildDocumentModelRequest,
        AzureBlobContentSource,
        DocumentModelDetails,
        )
from azure.core.credentials import AzureKeyCredential 

load_dotenv(find_dotenv())
training_folder_path = os.getenv('training_folder_path')
training_folder_path = training_folder_path.strip()
if not training_folder_path:
    raise ValueError("The SAS URI for the training folder path is missing")

# print(f"Training folder path: {training_folder_path}")

def build_model(training_folder_path):
    # [START build_model]
    # Load environment variables
    load_dotenv(find_dotenv())
    endpoint = os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT")
    key = os.getenv("DOCUMENTINTELLIGENCE_API_KEY")
    # container_sas_url = os.environ.get("CONTAINER_SAS_URL")

    # Create DocumentIntelligenceClient
    client = DocumentIntelligenceAdministrationClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    
    poller = client.begin_build_document_model(
    BuildDocumentModelRequest(
        model_id=str(uuid.uuid4()),
        build_mode=DocumentBuildMode.TEMPLATE,
        azure_blob_source=AzureBlobContentSource(container_url=training_folder_path),
        description="my model description",
    )
)
    model: DocumentModelDetails = poller.result()

    print(f"Model ID: {model.model_id}")
    print(f"Description: {model.description}")
    print(f"Model created on: {model.created_date_time}")
    print(f"Model expires on: {model.expiration_date_time}")
    if model.doc_types:
        print("Doc types the model can recognize:")
        for name, doc_type in model.doc_types.items():
            print(f"Doc Type: '{name}' built with '{doc_type.build_mode}' mode which has the following fields:")
            if doc_type.field_schema:
                for field_name, field in doc_type.field_schema.items():
                    if doc_type.field_confidence:
                        print(
                            f"Field: '{field_name}' has type '{field['type']}' and confidence score "
                            f"{doc_type.field_confidence[field_name]}"
                        )
    # [END build_model]
    return model.model_id

if __name__ == '__main__':
     # Load environment variables 
    load_dotenv(find_dotenv())
    training_folder_path = os.getenv('training_folder_path')
    build_model(training_folder_path)