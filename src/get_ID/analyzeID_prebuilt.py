import os
import logging
import yaml
from urllib.parse import urlparse
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def analyze_identity_documents(path_to_id_document):
    # Load environment variables
    endpoint = os.environ.get("DOCUMENTINTELLIGENCE_ENDPOINT")
    key = os.environ.get("DOCUMENTINTELLIGENCE_API_KEY")

    # Create DocumentIntelligenceClient
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    # Check if path_to_id_document is a URL or a local file path
    if bool(urlparse(path_to_id_document).scheme):  # If it's a URL
        poller = client.begin_analyze_document(
            "prebuilt-idDocument", 
            AnalyzeDocumentRequest(url_source=path_to_id_document)
        )
    else:  # Treat as a local file
        path_to_sample_documents = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", path_to_id_document))
        with open(path_to_sample_documents, "rb") as f:
            poller = client.begin_analyze_document(
                "prebuilt-idDocument",
                analyze_request=f,
                content_type="application/octet-stream"
            )

    id_documents: AnalyzeResult = poller.result()

    # Initialize the dictionary to store all results
    results = []

    # If documents are found, extract fields and their confidence
    if id_documents.documents:
        for idx, id_document in enumerate(id_documents.documents):
            document_info = {}
            document_info['document_index'] = idx + 1  # Keep track of the document index
            
            if id_document.fields:
                fields_to_extract = ["FirstName", "LastName", "DocumentNumber", "DateOfBirth", "DateOfExpiration", "Sex", "Address", "CountryRegion", "Region"]
                
                for field_name in fields_to_extract:
                    field = id_document.fields.get(field_name)
                    if field:
                        document_info[field_name] = {
                            'value': field.value_string or field.value_date or field.value_country_region,
                            'confidence': field.confidence
                        }
            
            results.append(document_info)

    return results

if __name__ == "__main__":
    from azure.core.exceptions import HttpResponseError
    from dotenv import find_dotenv, load_dotenv

    # Load environment variables
    try:
        load_dotenv(find_dotenv())
        path_to_id_document = os.environ.get("file_path_to_id")
        results = analyze_identity_documents(path_to_id_document)
        print(results)  # Display the dictionary with the captured values and confidence scores
    except HttpResponseError as error:
        # Handle HttpResponseError
        if error.error is not None:
            if error.error.code == "InvalidImage":
                print(f"Received an invalid image error: {error.error}")
            if error.error.code == "InvalidRequest":
                print(f"Received an invalid request error: {error.error}")
            raise
        if "Invalid request".casefold() in error.message.casefold():
            print(f"Uh-oh! Seems there was an invalid request: {error}")
        raise
