# import libraries
import os
import uuid
import json
import logging
from dotenv import dotenv_values, load_dotenv, find_dotenv
from urllib.parse import urlparse
from typing import Optional
from azure.storage.blob import BlobServiceClient
import src.utility.upload_files_to_blob as upload
import get_faces.video_indexer_client as indexer
import get_faces.face_api_client as faceAPI

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

# Load and define env parameters
load_dotenv(find_dotenv())
config = dotenv_values(".env")

def get_video_insights(file_path:str, local_dir:Optional[str]):
    logger.info('loading parameters for video indexer')
    # load parameters for video indexer
    arm_access_token = config.get("arm_access_token")
    AccountName = config.get('AccountName')
    ResourceGroup = config.get('ResourceGroup')
    SubscriptionId = config.get('SubscriptionId')
    ApiVersion = config.get('VI_ApiVersion')
    ApiEndpoint = config.get('VI_ApiEndpoint')
    AzureResourceManager = config.get('AzureResourceManager')

    # Azure Blob Storage configuration
    # logger.info('loading azure blob configuration')
    # blob_service_client_thumbnail = BlobServiceClient(account_url=config.get('thumbnail_container_URL'), credential=config.get('thumbnail_container_SAS_TOKEN'))
    # blob_service_client_json = BlobServiceClient(account_url=config.get('json_container_URL'), credential=config.get('json_container_SAS_TOKEN'))
    # blob_connection_string = config.get('AZURE_STORAGE_CONNECTION_STRING')

    # create and validate consts
    logger.info('authenticating video indexer')
    consts = indexer.Consts(ApiVersion, ApiEndpoint, AzureResourceManager, AccountName, ResourceGroup, SubscriptionId)
    # Authenticate
    # create Video Indexer Client
    vi_client = indexer.VideoIndexerClient()
    # Get access tokens (arm and Video Indexer account)
    vi_client.get_access_token(consts)

    logger.info('upload and index the video and get insights')
    # Upload the video   
    video_id = vi_client.upload_video(file_path)  
    # Index the uploaded video
    vi_client.index_video(video_id) 
    # Get video insights and store them in a variable
    insights = vi_client.get_video_insights(video_id)  
    
    ####### This snippet will upload insights to blob storage. Comment out if it's not needed. ##########
    '''
    # Convert the insights dictionary to a JSON string
    json_file_data = json.dumps(insights)
    # Set the file name based on insights data 
    json_file_name = f'{insights["video_id"]}.json'  # using 'video_id' field in insights
    # Upload the JSON data to a blob storage
    json_container_name = config.get('json_container_name')
    uploaded_json_url = upload.upload_json_to_blob(blob_service_client=blob_service_client_json, 
                                                   container_name=json_container_name, 
                                                   json_data = json_file_data, 
                                                   file_name = json_file_name)
    print(f"Uploaded JSON URL: {uploaded_json_url}")
    '''
    ###########################################################

    # Retrieve face thumbnails
    logger.info('Retrieve face thumbnails')
    thumbnails = vi_client.get_face_images(insights, video_id)  

    ####### This snippet will upload thumbnails to blob storage. Comment out if it's not needed. ##########
    '''
    # Create unique file names for each image
    file_names = [f"image_{i}.png" for i in range(len(thumbnails))]
    # Upload face thumbnails to blob storage
    thumbnail_container_name = config.get('thumbnail_container_name')
    uploaded_image_urls = upload.upload_images_list(blob_service_client=blob_service_client_thumbnail, 
                                             container_name=thumbnail_container_name, 
                                             images=thumbnails, 
                                             file_names=file_names)
    # Print the uploaded image URLs
    print(f"Uploaded images URLs: {uploaded_image_urls}")
    '''
    ###########################################################

    ####### This snippet will save thumbnails locally. Comment out if it's not needed. ##########
    # '''
    # save images locally
    logger.info('save thumbnails locally')
    upload.save_thumbnails_locally(local_dir, thumbnails)
    # retrive files
    file_list = upload.get_files_from_directory(local_dir)
    # '''
    ###########################################################
    logger.info('get emotion and sentiment data')
    # Get emotions from the video insights
    emotions = vi_client.get_emotions_from_insights(insights)  
    
    # Get sentiments from the video insights
    sentiments = vi_client.get_sentiments_from_insights(insights)  

    return file_list, emotions, sentiments

def build_person_model(file_list:list):
    logger.info('load parameters for Face API')
    # load parameters for Face API
    endpoint = config.get("FACE_ENDPOINT_URL")
    subscription_key = config.get("FACE_API_KEY")
    face_api_version = config.get('face_api_version')

    # Create a unique person group ID
    logger.info('Create a unique person group ID')
    person_group_id = str(uuid.uuid4())

    # build person model based on the images extracted from the video
    logger.info('build person model based on the images extracted from the video')
    faceAPI.build_person_model(person_group_id=person_group_id, image_sources=file_list)

    return person_group_id

def indentify_faces(image_source:str, person_group_id:str):
    # identify a face from an ID with images extracted from the video  
    results = faceAPI.identify_faces_in_person_group(image_source, person_group_id)
    logger.info(f'face_results: {results}')

    for match in results:
        face_id = match['faceId']
        for candidate in match['candidates']:
            confidence = candidate['confidence']
            print(f"The Identity match for face ID {face_id} has a confidence of {confidence:.4f}")

    return results

# Run the main function
if __name__ == "__main__":
    video_file_path = config.get('LocalVideoPath')
    local_dir = config.get('local_thumbnails_dir_path')

    # get video insights
    file_list, emotions, sentiments = get_video_insights(video_file_path, local_dir)

    # build person model based on the images extracted from the video
    person_group_id = build_person_model(file_list)

    # get id image source file
    id_source_file = config.get("image_id")
    
    # identify faces between the id image and person Model
    indentify_faces(id_source_file, person_group_id) 

    # delete the person_group
    faceAPI.delete_person_group(person_group_id)
