import os
import pandas as pd
import logging
import yaml
from dateutil import parser
from datetime import date
from typing import Optional
from dotenv import find_dotenv, load_dotenv
from get_custom_text.analyze_custom_doc_main import main as analyze_custom
from src.get_ID.analyzeID_prebuilt import analyze_identity_documents as analyze_id
from get_faces.face_identification_main import get_video_insights as insights
from get_faces.face_identification_main import build_person_model as personModel
from get_faces.face_identification_main import indentify_faces as identify_faces
# import step_4.lighter_detection 

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

# Load flight manifest table
manifest_path = config_yml['manifest_file']['file_path']
manifest_df = pd.read_csv(manifest_path)

# Function to perform 3-Way Person Name Validation for a single row
def validate_name(id_data: list, bp_data: list, manifest_row: pd.Series) -> bool:
    logger.info("Name Validation")

    # Extract first word for first name and last word for last name from the ID
    id_info = id_data[0]
    id_first_name = id_info.get('FirstName', {}).get('value', '').strip().split()[0].upper()
    id_last_name = id_info.get('LastName', {}).get('value', '').strip().split()[-1].upper()

    # Extract first word for first name and last word for last name from the boarding pass
    bp_info = bp_data[0]
    bp_first_name = bp_info.get('fields', {}).get('First Name', {}).get('value', '').strip().split()[0].upper()
    bp_last_name = bp_info.get('fields', {}).get('Last Name', {}).get('value', '').strip().split()[-1].upper()

    # Extract first and last names from the manifest row
    manifest_first_name = manifest_row['First Name'].strip().split()[0].upper()
    manifest_last_name = manifest_row['Last Name'].strip().split()[-1].upper()

    # Validate first and last names
    if manifest_first_name == id_first_name and manifest_last_name == id_last_name:
        if manifest_first_name == bp_first_name and manifest_last_name == bp_last_name:
            logger.info(f"Name Matched: ID({id_first_name} {id_last_name}), BP({bp_first_name} {bp_last_name}), Manifest ({manifest_first_name} {manifest_last_name})")
            return True  # All names match

    logger.info(f"Name mismatch: ID({id_first_name} {id_last_name}), BP({bp_first_name} {bp_last_name}), Manifest ({manifest_first_name} {manifest_last_name}) did not match.")
    return False

# Function to perform DoB Validation
def validate_dob(id_data: list, manifest_row: pd.Series) -> bool:
    logger.info("DoB Validation")
    try:
        # Extract Date of Birth from the ID
        id_info = id_data[0]
        id_dob = id_info.get('DateOfBirth', {}).get('value', None)

        if isinstance(id_dob, date):
            id_dob_standardized = id_dob.strftime('%Y-%m-%d')
        else:
            try:
                id_dob_standardized = parser.parse(id_dob).strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error parsing ID DoB: {str(e)}")
                return False

        # Standardize manifest DOB
        manifest_dob = manifest_row['Date of Birth']
        if isinstance(manifest_dob, date):
            manifest_dob_standardized = manifest_dob.strftime('%Y-%m-%d')
        else:
            try:
                manifest_dob_standardized = parser.parse(manifest_dob).strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error parsing manifest DoB: {str(e)}")
                return False

        if id_dob_standardized == manifest_dob_standardized:
            logger.info(f"DoB Matched. id_dob({id_dob_standardized}), manifest_dob({manifest_dob_standardized})")
            return True

        logger.info(f"DoB Mismatch: ID({id_dob_standardized}), Manifest({manifest_dob_standardized}) did not match.")
        return False

    except Exception as e:
        logger.error(f"Error during DoB validation: {str(e)}")
        return False


# Function to perform Boarding Pass Validation
def validate_boarding_pass(bp_data: list, manifest_row: pd.Series) -> bool:
    logger.info("Boarding Pass Validation")
    columns_to_check = {
        'Flight_No': 'Flight No.',
        'Seat': 'Seat',
        'Origin': 'From',
        'Destination': 'To',
        'First Name': 'First Name',
        'Last Name': 'Last Name'
    }

    bp_info = bp_data[0]
    for bp_field, manifest_column in columns_to_check.items():
        bp_value = bp_info.get('fields', {}).get(bp_field, {}).get('value', '').strip().upper()
        manifest_value = str(manifest_row[manifest_column]).strip().upper()

        if bp_value != manifest_value:
            logger.info("Boarding Pass not Matched. bp_value:{bp_value}, manifest_value:{manifest_value}")
            return False
    logger.info("Boarding Pass Matched")
    return True

# Function to perform Person Identity Validation
def validate_person_identity(face_results:list)->bool:
    logger.info("Face Validation")
    if face_results:
        for face in face_results:
            for candidate in face.get('candidates', []):
                if candidate['confidence'] >= 0.65:
                    logger.info("Face Matched")
                    return True
    logger.info("Face not Matched")
    return False 

# If the cofidence score =>0.65 is sent as parameters along with the body when sending API request to the Azure FaceAPI,
# then if there's any values in the response, they will always have a confidence of more than 0.65. In that case, the following 
# function will also work. 
'''def validate_person_identity(face_results:list)->bool:
    logger.info("Face Validation")
    if face_results:
        return True 
    return False'''
    

# Function to validate luggage (stubbed for now)
def validate_luggage():
    return False  # Leave as False since we do not have a way to verify luggage

# Function to update validation results in the manifest
def update_manifest_table(manifest_df, index, validation_results):
    # Update validation columns in the manifest dataframe
    manifest_df.at[index, 'NameValidation'] = validation_results.get('NameValidation')
    manifest_df.at[index, 'DoBValidation'] = validation_results.get('DoBValidation')
    manifest_df.at[index, 'BoardingPassValidation'] = validation_results.get('BoardingPassValidation')
    manifest_df.at[index, 'PersonValidation'] = validation_results.get('PersonValidation')
    manifest_df.at[index, 'LuggageValidation'] = validation_results.get('LuggageValidation')
    
    # Check majority rule: if 3 or more validations are True, set ValidationStatus to True
    passed_validations = sum([v for k, v in validation_results.items() if v])
    manifest_df.at[index, 'ValidationStatus'] = passed_validations >= 4

# Main function for validation
def validate_all(id_data, boarding_pass_data, face_results, manifest_df):
    logger.info("Starting validation process...")
    passenger_info = {}  # Initialize passenger_info as a dictionary

    # Iterate over each passenger in the manifest and perform validations
    for index, passenger in manifest_df.iterrows():
        validation_results = {
            "NameValidation": validate_name(id_data, boarding_pass_data, passenger),
            "DoBValidation": validate_dob(id_data, passenger),
            "BoardingPassValidation": validate_boarding_pass(boarding_pass_data, passenger),
            "PersonValidation": validate_person_identity(face_results),
            "LuggageValidation": validate_luggage()
        }

        # Update the manifest table with the validation results
        update_manifest_table(manifest_df, index, validation_results)
        
        try:
            # Ensure manifest_df is not empty after validation
            if manifest_df.empty:
                logger.error("The manifest DataFrame is empty after validation.")
                return None
            elif manifest_df.at[index, 'ValidationStatus']:
                passenger_info = {
                    "FirstName": passenger['First Name'],
                    "LastName": passenger['Last Name'],
                    "FlightNo": passenger['Flight No.'],
                    "BoardingTime": passenger['Boarding Time'],
                    "From": passenger['From'],
                    "To": passenger['To'],
                    "Seat": passenger['Seat'],
                    "NameValidation": manifest_df.at[index, 'NameValidation'], 
                    "DoBValidation": manifest_df.at[index, 'DoBValidation'], 
                    "PersonValidation": manifest_df.at[index, 'PersonValidation'], 
                    "BoardingPassValidation": manifest_df.at[index, 'BoardingPassValidation'], 
                    "LuggageValidation": manifest_df.at[index, 'LuggageValidation'], 
                    "ValidationStatus": manifest_df.at[index, 'ValidationStatus']
                }
                logger.info(f"Validation successful for row {index}. Returning passenger info.")
                print(passenger_info)
                return passenger_info
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return None
    
    logger.info("No valid rows found.")
    return None

def get_validation_messages(passenger_info, environment="console"):
    # Set the newline character based on the environment
    newline = "\n" if environment == "console" else "<br>"

    try:
        if not passenger_info:
            return (
                "Some of the information provided does not match our records or your identity "
                f"could not be verified.{newline}Please see a customer service representative."
            )

        # Access values from the passenger_info dictionary
        first_name = passenger_info['FirstName']
        last_name = passenger_info['LastName']
        flight_no = passenger_info['FlightNo']
        boarding_time = passenger_info['BoardingTime']
        origin = passenger_info['From']
        destination = passenger_info['To']
        seat = passenger_info['Seat']
        validation_status = passenger_info['ValidationStatus']
        name_validation = passenger_info['NameValidation']
        dob_validation = passenger_info['DoBValidation']
        boarding_pass_validation = passenger_info['BoardingPassValidation']
        person_validation = passenger_info['PersonValidation']
        luggage_validation = passenger_info['LuggageValidation']

        # Generate message based on validation flags
        if name_validation and dob_validation and boarding_pass_validation:
            if person_validation and luggage_validation:
                message = (
                    f"Dear {first_name} {last_name},{newline}"
                    f"You are welcome to flight #{flight_no} leaving at {boarding_time}.{newline}"
                    f"From {origin} to {destination}, your seat number is {seat}, and it is confirmed.{newline}"
                    f"We did not find a prohibited item (lighter) in your carry-on baggage.{newline}"
                    "Your identity is verified, please board the plane."
                )
            elif person_validation and not luggage_validation:
                message = (
                    f"Dear {first_name} {last_name},{newline}"
                    f"You are welcome to flight #{flight_no} leaving at {boarding_time}.{newline}"
                    f"From {origin} to {destination}, your seat number is {seat}, and it is confirmed.{newline}"
                    f"We have found a prohibited item in your carry-on baggage, and it is flagged for removal.{newline}"
                    "Your identity is verified. However, your baggage verification failed, so please see a customer service representative."
                )
            elif not person_validation and luggage_validation:
                message = (
                    f"Dear {first_name} {last_name},{newline}"
                    f"You are welcome to flight #{flight_no} leaving at {boarding_time}.{newline}"
                    f"From {origin} to {destination}, your seat number is {seat}, and it is confirmed.{newline}"
                    f"We did not find a prohibited item (lighter) in your carry-on baggage.{newline}"
                    "However, your identity could not be verified. Please see a customer service representative."
                )
        elif not name_validation or not dob_validation:
            message = (
                f"Dear Sir/Madam,{newline}"
                "Some of the information on your ID card does not match the flight manifest data, so you cannot board the plane.{newline}"
                "Please see a customer service representative."
            )
        elif not boarding_pass_validation:
            message = (
                f"Dear Sir/Madam,{newline}"
                "Some of the information in your boarding pass does not match the flight manifest data, so you cannot board the plane.{newline}"
                "Please see a customer service representative."
            )
        return message

    except Exception as e:
        logger.error(f"Error generating validation message: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
        logger = logging.getLogger()

        # Load the flight manifest table
        manifest_path = config_yml['manifest_file']['file_path']
        manifest_df = pd.read_csv(manifest_path)

        # get ID data
        path_to_id_document = os.getenv("file_path_to_id")
        if not path_to_id_document:
            raise FileNotFoundError("ID document file path is not found in environment variables.")
        id_data = analyze_id(path_to_id_document)

        # get boarding data
        model_id = config_yml['doc_intelligence']['custom_models']['boarding_pass_1']
        training_folder_path = os.getenv('training_folder_path')
        path_to_custom_document = os.getenv("file_path_boarding_pass")
        if not path_to_custom_document:
            raise FileNotFoundError("Boarding pass file path is not found in environment variables.")
        bp_info = analyze_custom(path_to_custom_document, model_id, training_folder_path)

        # get video faces
        video_file_path = config_yml['video_indexer']['video_path']
        local_dir = os.getenv('local_thumbnails_dir_path')
        # Get video insights
        image_list = insights(video_file_path, local_dir)
        # Build person model based on the images extracted from the video
        person_group_id = personModel(image_list)
        # Get ID image source file
        id_source_file = os.getenv("file_path_to_id")
        if not id_source_file:
            raise FileNotFoundError("ID source file is not found in environment variables.")
        # Identify faces between the ID image and person model
        face_results = identify_faces(id_source_file, person_group_id)

        # validate all sources
        validate_all(id_data, bp_info, face_results, manifest_df)
    except Exception as e:
        logger.error(f"An error occurred during validation: {str(e)}")
        raise
