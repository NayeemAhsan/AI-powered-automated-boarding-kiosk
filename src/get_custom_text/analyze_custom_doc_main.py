import os
import logging
import yaml
from urllib.parse import urlparse
from typing import Optional
from dotenv import find_dotenv, load_dotenv
from get_custom_text.buildCustomModel import build_model as build
from get_custom_text.extract_custom_doc import analyze_custom_documents as analyze

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def main(path_to_id_document:str, model_id:Optional[str], training_folder_path:Optional[str]) -> list:
    from azure.core.exceptions import HttpResponseError

    try:
        logger.info('Build a custom model if no existing model is specified')
        # Build a custom model if no existing model is specified
        if model_id is None:
            if training_folder_path is None:
                logger.info('Training folder path to build custom model is missing.')
                raise error
            model_id = build(training_folder_path)

        # Analyze documents using the created or provided model
        logger.info('Extract text based on the custom model')
        doc_info = analyze(model_id, path_to_id_document)

    except HttpResponseError as error:
        # Handle error responses with code-specific details
        if error.error is not None:
            if error.error.code == "InvalidImage":
                print(f"Invalid image error: {error.error}")
            elif error.error.code == "InvalidRequest":
                print(f"Invalid request error: {error.error}")
            raise
        elif "Invalid request".casefold() in error.message.casefold():
            print(f"Invalid request: {error}")
        raise
    return doc_info

if __name__ == "__main__":
    logger.info('get the env variables and config file')
    # Load the config file
    with open('./config.yaml') as yaml_file:
        config = yaml.safe_load(yaml_file)
    model_id = config['doc_intelligence']['custom_models']['boarding_pass_1']
    # Load environment variables 
    load_dotenv(find_dotenv())
    training_folder_path = os.getenv('training_folder_path')
    path_to_id_document = os.getenv("file_path_boarding_pass")  # SAS URL or local path
    main(path_to_id_document, model_id, training_folder_path)
    
