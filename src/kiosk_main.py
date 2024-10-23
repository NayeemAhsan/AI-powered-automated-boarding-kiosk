import os
import time
import pandas as pd
import logging
import yaml
from dotenv import find_dotenv, load_dotenv
from get_custom_text.analyze_custom_doc_main import main as analyze_custom
from src.get_ID.analyzeID_prebuilt import analyze_identity_documents as analyze_id
from get_faces.face_identification_main import get_video_insights as insights
from get_faces.face_identification_main import build_person_model as personModel
from get_faces.face_identification_main import indentify_faces as identify_faces
# import step_4.lighter_detection
from validation.validation import validate_all, get_validation_messages

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

# Load environment variables
load_dotenv(find_dotenv())

# Get the config file path from the .env file
config_path = os.getenv('CONFIG_PATH')

# Load the config file
if config_path and os.path.exists(config_path):
    with open(config_path) as yaml_file:
        config_yml = yaml.safe_load(yaml_file)
else:
    raise FileNotFoundError(f"Config file not found at the specified path: {config_path}")

def load_manifest_file():
    try:
        manifest_path = config_yml['manifest_file']['file_path']
        if not manifest_path:
            raise FileNotFoundError("Manifest file path is missing in the config.")
        manifest_df = pd.read_csv(manifest_path)
        if manifest_df.empty:
            logger.error("The manifest file is empty.")
            return None
        # Generate timestamp for file naming
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        new_filename = f"{manifest_path.split('.')[0]}_{timestamp}.csv"
        manifest_df.to_csv(new_filename, index=False)
    except FileNotFoundError as e:
        logger.error(f"Manifest file not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error loading manifest file: {str(e)}")
        raise
    return manifest_df

def get_id(id_file_path):
    try:
        if not id_file_path:
            raise FileNotFoundError("ID document file path is not provided.")
        id_data = analyze_id(id_file_path)
        print(id_data)  # Display the dictionary with the captured values and confidence scores
    except FileNotFoundError as e:
        logger.error(f"ID document file not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing ID document: {str(e)}")
        raise
    return id_data


def get_boarding_pass(boarding_pass_file_path):
    try:
        model_id = config_yml['doc_intelligence']['custom_models']['boarding_pass_1']
        training_folder_path = os.getenv('training_folder_path')

        if not boarding_pass_file_path:
            raise FileNotFoundError("Boarding pass file path is not provided.")
        bp_info = analyze_custom(boarding_pass_file_path, model_id, training_folder_path)
        print(bp_info)  # Display the dictionary with the captured values and confidence scores
    except FileNotFoundError as e:
        logger.error(f"Boarding pass file not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing custom document: {str(e)}")
        raise
    return bp_info

def identify_faces_from_video(video_file_path, id_source_file):
    try:
        local_dir = os.getenv('local_thumbnails_dir_path')

        if not video_file_path:
            raise FileNotFoundError("Video file path is missing.")
        if not local_dir:
            raise FileNotFoundError("Local thumbnails directory path is missing in environment variables.")

        # Get video insights
        image_list, emotions, sentiments = insights(video_file_path, local_dir)

        # Build person model based on the images extracted from the video
        person_group_id = personModel(image_list)

        # Get ID image source file
        # id_source_file = os.getenv("file_path_to_id")
        if not id_source_file:
            raise FileNotFoundError("ID source file is not found in environment variables.")

        # Identify faces between the ID image and person model
        face_results = identify_faces(id_source_file, person_group_id)
    except FileNotFoundError as e:
        logger.error(f"File not found during face verification: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error during face verification: {str(e)}")
        raise
    return face_results

def main(id_file_path, boarding_pass_file_path, video_file_path):
    try:
        # Load the manifest file
        logger.error("Load the manifest file")
        manifest_file = load_manifest_file()

        # Get the ID documents
        logger.error("Extract the ID documents")
        id_data = get_id(id_file_path)

        # Get the boarding pass info
        logger.error("Extract the boarding pass info")
        boarding_pass_data = get_boarding_pass(boarding_pass_file_path)

        # Verify faces
        logger.error("Identify faces")
        # face_results = identify_faces_from_video(video_file_path, id_file_path)
        face_results = [{'faceId': '8344e744-601c-4f4e-905b-aaf21c3f16b0', 'candidates': [{'personId': 'eac60023-b565-449f-be9d-af25a2524185', 'confidence': 0.95612}]}]

        # Perform validation
        logger.error("Perform validation")
        passenger_info = validate_all(id_data, boarding_pass_data, face_results, manifest_file)

        # Get the validation message
        logger.error("Generate validation message")
        validation_message = get_validation_messages(passenger_info)
        # print(validation_message)
        return validation_message
    except Exception as e:
        logger.error(f"An error occurred in the main function: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        main(id_file_path, boarding_pass_file_path, video_file_path)
    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}")
        raise
