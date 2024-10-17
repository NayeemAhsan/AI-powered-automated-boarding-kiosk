import requests
import uuid
import os
import sys
import time
import yaml
import logging
import string
import random
import numpy as np
from PIL import Image, ImageDraw
import io
from urllib.parse import urlparse, urlencode
from dotenv import dotenv_values, load_dotenv, find_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

# Load and define env parameters
load_dotenv(find_dotenv())
config = dotenv_values(".env")

# Get the config file path from the .env file
config_path = os.getenv('CONFIG_PATH')

# Load the config file
if config_path and os.path.exists(config_path):
    with open(config_path) as yaml_file:
        config_yml = yaml.safe_load(yaml_file)
else:
    raise FileNotFoundError(f"Config file not found at the specified path: {config_path}")

# Azure Face API Configuration
subscription_key = config.get("FACE_API_KEY")
endpoint = config.get("FACE_ENDPOINT_URL")
face_api_version = config.get('face_api_version')

def create_person_group_name(person_group_id:str, length=random.randint(12, 128))->str:
  """Generates a random string with a timestamp and person's name.

  Args:
    person_group_id: The person_group_id to include in the string.
    length: The desired length of the string (between 12 and 128 characters).

  Returns:
    A random string with a timestamp and person's name.
  """

  # Get the current timestamp as a string
  timestamp = str(time.time())

  # Calculate the remaining length for the random string
  remaining_length = length - len(timestamp) - len(person_group_id)

  # Generate a random string of the remaining length
  random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=remaining_length))

  # Combine the timestamp, person's name, and random string
  person_group_name = timestamp + person_group_id + random_string
  return person_group_name

def create_person_group(person_group_id:str, person_group_name:str):
    """
    Create a new Person Group.
    
    Args:
    - person_group_id: Unique ID for the person group.
    - person_group_name: Name for the person group.
    
    Returns:
    - Status of person group creation
    """
    person_group_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
        }
    body = {"name": person_group_name, "recognitionModel": config_yml['face_api']['recognitionModel']}
    
    response = requests.put(person_group_url, headers=headers, json=body)
    return response.status_code, response.text

def delete_person_group(person_group_id:str):
    '''
    Delete a person group
    '''
    person_group_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
        }
    
    response = requests.delete(person_group_url, headers=headers)
    
    if response.status_code == 200:
        print(f"Person Group {person_group_id} deleted successfully.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

def add_person_to_group(person_group_id:str, person_name:str)->str:
    """
    Add a new person to a Person Group.
    
    Args:
    - person_group_id: ID of the person group.
    - person_name: Name of the person to be added.
    
    Returns:
    - Person ID of the newly added person
    """
    add_person_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/persons"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
        }
    body = {"name": person_name}
    
    response = requests.post(add_person_url, headers=headers, json=body)
    personID = response.json()["personId"]
    return personID

def delete_person(person_group_id:str, person_id:str):
    '''
    Delete a person from a person group
    '''
    url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/persons/{person_id}"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
        }
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Person {person_id} deleted successfully from person group {person_group_id}.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

def add_face_to_person(person_group_id:str, person_id:str, image_source:str):
    """
    Add a face to a person in the Person Group.
    
    Args:
    - person_group_id: ID of the person group.
    - person_id: ID of the person.
    - image_source: URL or path to the image.
    - image_type: Specify 'url', 'session', or 'local' (default is 'url').
    
    Returns:
    - Status of adding face
    """
    face_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/persons/{person_id}/persistedFaces"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
        }
    
    if bool(urlparse(image_source).scheme):  # If the image source is a URL
        body = {"url": image_source}
        response = requests.post(face_url, headers=headers, json=body)
    elif os.path.isfile(image_source): # If the image source is local
        with open(image_source, 'rb') as image_file:
            response = requests.post(face_url, headers=headers, data=image_file)
            return response.json()
    else: # the image source is a session ID
        response = requests.post(face_url, headers=headers, data=image_source)
    
    persistedFaceId = response.json()["persistedFaceId"]
    
    return response.status_code, persistedFaceId

def delete_face(person_group_id:str, person_id:str, persisted_face_id:str):
    '''
    Delete a face from a person group
    '''
    url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/persons/{person_id}/persistedFaces/{persisted_face_id}"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
        }
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Face {persisted_face_id} deleted successfully from person {person_id} in person group {person_group_id}.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

def train_person_group(person_group_id:str):
    """
    Train the Person Group to recognize persons and faces.
    
    Args:
    - person_group_id: ID of the person group to be trained.
    
    Returns:
    - Status of the training process
    """
    train_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/train"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
        }
    response = requests.post(train_url, headers=headers)
    return response.status_code, response.text

def get_training_status(person_group_id:str):
    """
    Get the status of the person group training.
    
    Args:
    - person_group_id: ID of the person group.
    
    Returns:
    - Training status (JSON)
    """
    status_url = f"{endpoint}/face/{face_api_version}/persongroups/{person_group_id}/training"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
        }
    while True:
        response = requests.get(status_url, headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"Error in check_training_status: {err.response.text}")
            raise
        return response.json()

def build_person_model(person_group_id:str, image_sources:list):
    """
    This function builds a person model in Azure Face API by:
    1. Creating a person group.
    2. Adding a person to the group.
    3. Adding faces to the person group.
    4. Training the person group.

    Parameters:
    - subscription_key: Azure Face API subscription key.
    - endpoint: Azure Face API endpoint.
    - person_group_id: ID of the person group to be created.
    - person_name: Name of the person to be added to the group.

    Returns:
    - person_id: The ID of the created person.
    """
    # Step 1: Create a person group
    logger.info('Create a person group')
    person_group_name = create_person_group_name(person_group_id)
    create_person_group(person_group_id, person_group_name)

    # Step 2: Add person to the group
    logger.info('Add person to the group')
    person_id = add_person_to_group(person_group_id, person_group_name)
    print(f"Person {person_group_name} added with Person ID: {person_id}")

    # Step 3: Add faces to the person
    logger.info('Add faces to the person')
    for images in image_sources:
        face_id = add_face_to_person(person_group_id, person_id, images)
        print(f"Face added with Face ID: {face_id}")

    # Step 4: Train the person group
    logger.info('Train the person group')
    train_person_group(person_group_id)

    # Wait for training to finish.
    logger.info('Wait for training to finish')
    while (True):
        training_status = get_training_status(person_group_id)
        print("Training status: {}.".format(training_status['status']))
        if (training_status['status'] == 'succeeded'):
            print(f"Training person group {person_group_id}...")
            print("Person group training complete.")
            break
        elif (training_status['status'] == 'failed'):
            delete_person_group(person_group_id=person_group_id)
            sys.exit('Training the person group has failed.')
        time.sleep(5)
    
    return person_id

def detect_faces(image_source:str):
    """
    Detect faces from a URL, session ID, or local file.
    
    Args:
    - image_source: Image URL, session ID, or local file path.
    - image_type: Specify 'url', 'session', or 'local' (default is 'url').
    
    Returns:
    - Face detection result (JSON)
    """
    params = {
        'recognitionModel': config_yml['face_api']['recognitionModel'],
        'returnFaceId': 'true',
        'returnFaceLandmarks': config_yml['face_api']['returnFaceLandmarks']
        }
    query_string = urlencode(params)
    face_url = f"{endpoint}/face/{face_api_version}/detect?{query_string}"
    
    if bool(urlparse(image_source).scheme):  # If the image source is a URL
        headers = {
                'Ocp-Apim-Subscription-Key': subscription_key,
                'Content-Type': 'application/json'
                }
        body = {"url": image_source}
        response = requests.post(face_url, headers=headers, json=body)
    elif os.path.isfile(image_source): # If the image source is local
        with open(image_source, 'rb') as image_file:
            headers = {
                    'Ocp-Apim-Subscription-Key': subscription_key,
                    'Content-Type': 'application/octet-stream'
                    }
            response = requests.post(face_url, headers=headers, data=image_file)
    else: # the image source is a session ID
        headers = {
                'Ocp-Apim-Subscription-Key': subscription_key,
                'Content-Type': 'application/json'
                }
        body = {"data": image_source}
        response = requests.post(face_url, headers=headers, json=body)
    return response.json()

# Function to detect and identify faces in a person group
def identify_faces_in_person_group(image_source:str, person_group_id:str):
    """
    Identify faces in a person group.
    
    Args:
    - image_source: Image URL or local file path.
    - image_type: Specify 'url', 'local', or 'session'.
    - person_group_id: ID of the person group.
    
    Returns:
    - Identification result (JSON)
    """
    # Detect face first
    logger.info('Detecting faces')
    detected_faces = detect_faces(image_source)
    
    if not detected_faces:
        print("No faces detected.")
        return None
    logger.info(f'detected_faces: {detected_faces}')
    # Get face IDs from detected faces
    logger.info('Get face IDs from detected faces')
    face_ids = [face['faceId'] for face in detected_faces]
    
    # Call identify API
    logger.info('Call identify API to identify faces between the source id and the detected faces')
    identify_url = f"{endpoint}/face/{face_api_version}/identify"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key
        }
    body = {
        "personGroupId": person_group_id,
        "faceIds": face_ids,
        "maxNumOfCandidatesReturned": config_yml['face_api']['maxNumOfCandidatesReturned'],
        "confidenceThreshold": config_yml['face_api']['confidenceThreshold']
    }
    
    response = requests.post(identify_url, headers=headers, json=body)
    return response.json()

# Function to verify if two faces belong to the same person
def verify_faces(face_id1:str, face_id2:str):
    """
    Verify if two faces belong to the same person.
    
    Args:
    - face_id1: Face ID of the first person.
    - face_id2: Face ID of the second person.
    
    Returns:
    - Verification result (JSON)
    """
    verify_url = f"{endpoint}/face/{face_api_version}/verify"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
        }
    body = {
        "faceId1": face_id1,
        "faceId2": face_id2
    }
    
    response = requests.post(verify_url, headers=headers, json=body)
    return response.json()

# Function to draw a red rectangle around detected face
def draw_rectangle_around_face(image_source:str, image_type='url', faces=None, session_id=None):
    """
    Draw a red rectangle around the detected faces.
    
    Args:
    - image_source: Image URL or local file path.
    - image_type: Specify 'url', 'local', or 'session'.
    - faces: List of detected faces (faceRectangle data).
    - session_id: (Optional) Session Image ID for session-based images.
    
    Returns:
    - Image with red rectangles drawn around faces
    """
    
    # Get the image based on the type
    if os.path.isfile(image_source): # If the image source is local
        image = Image.open(image_source)
    else:
        image = Image.open(io.BytesIO(requests.get(image_source).content))
    
    # Initialize drawing context on the image
    draw = ImageDraw.Draw(image)
    
    # Draw red rectangle around detected faces
    if faces:
        for face in faces:
            rect = face['faceRectangle']
            # Draw rectangle (left, top, right, bottom)
            draw.rectangle(
                [
                    (rect['left'], rect['top']), 
                    (rect['left'] + rect['width'], rect['top'] + rect['height'])
                ], 
                outline="red", width=10
            )
    
    # Return the modified image with drawn rectangles
    return image