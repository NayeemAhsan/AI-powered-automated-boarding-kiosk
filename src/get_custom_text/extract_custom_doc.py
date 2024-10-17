import os
from urllib.parse import urlparse
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest

def analyze_custom_documents(custom_model_id, path_to_id_document):
    # Load environment variables
    endpoint = os.environ["DOCUMENTINTELLIGENCE_ENDPOINT"]
    key = os.environ["DOCUMENTINTELLIGENCE_API_KEY"]
    # model_id = os.getenv("CUSTOM_BUILT_MODEL_ID", custom_model_id)

    # Create client
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    # Check if path_to_id_document is a URL or a local file path
    if bool(urlparse(path_to_id_document).scheme):  # If it's a URL
        poller = client.begin_analyze_document(
            model_id, 
            AnalyzeDocumentRequest(url_source=path_to_id_document)
        )
    else:  # Treat as a local file
        path_to_sample_documents = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", path_to_id_document))
        with open(path_to_sample_documents, "rb") as f:
            poller = client.begin_analyze_document(
                model_id=custom_model_id,
                analyze_request=f,
                content_type="application/octet-stream"
            )

    result: AnalyzeResult = poller.result()

    # Initialize the list to store results
    analyzed_documents = []

    if result.documents:
        for idx, document in enumerate(result.documents):
            document_info = {
                "document_index": idx + 1,
                "doc_type": document.doc_type,
                "confidence": document.confidence,
                "model_id": result.model_id
            }

            if document.fields:
                fields_info = {}
                for name, field in document.fields.items():
                    field_value = field.value_string or field.content
                    fields_info[name] = {
                        "value": field_value,
                        "confidence": field.confidence
                    }
                
                document_info["fields"] = fields_info

            analyzed_documents.append(document_info)
    else:
        print("No documents were recognized in the result.")

    return analyzed_documents

if __name__ == "__main__":
    from azure.core.exceptions import HttpResponseError
    from dotenv import find_dotenv, load_dotenv
    import logging
    import yaml

    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
    logger = logging.getLogger()

    # Load environment variables
    try:
        logger.info('get the env variables and config file')
        # Load the config file
        with open('./config.yaml') as yaml_file:
            config = yaml.safe_load(yaml_file)
        model_id = config['doc_intelligence']['custom_models']['boarding_pass_1']
        # Load environment variables 
        load_dotenv(find_dotenv())
        if model_id is None:
            logger.info('custom_model_id is missing. Either provide the id or build a new model')
            raise

        # Analyze documents using the created or provided model
        logger.info('Extract text based on the custom model')
        path_to_id_document = os.getenv("file_path_boarding_pass")  # SAS URL or local path
        results = analyze_custom_documents(model_id, path_to_id_document)
        print(results)  # Print the results list with extracted fields and confidence scores
    except HttpResponseError as error:
        # Handle HttpResponseError
        print(f"HttpResponseError: {error}")
        raise
