import os
import requests
import time
from dotenv import load_dotenv, find_dotenv, dotenv_values
from typing import Optional
from tabulate import tabulate
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse
from dataclasses import dataclass
from azure.identity import DefaultAzureCredential

@dataclass
class Consts:
    ApiVersion: str
    ApiEndpoint: str
    AzureResourceManager: str
    AccountName: str
    ResourceGroup: str
    SubscriptionId: str

def get_arm_access_token(consts:Consts) -> str:
        '''
        Get an access token for the Azure Resource Manager
        Make sure you're logged in with `az` first

        :param consts: Consts object
        :return: Access token for the Azure Resource Manager
        '''
        credential = DefaultAzureCredential()
        scope = f"{consts.AzureResourceManager}/.default" 
        token = credential.get_token(scope)
        return token.token

def get_account_access_token(consts, arm_access_token, permission_type='Contributor', scope='Account',
                                   video_id=None):
    '''
    Get an access token for the Video Indexer account
    
    :param consts: Consts object
    :param arm_access_token: Access token for the Azure Resource Manager
    :param permission_type: Permission type for the access token
    :param scope: Scope for the access token
    :param video_id: Video ID for the access token, if scope is Video. Otherwise, not required
    :return: Access token for the Video Indexer account
    '''

    headers = {
        'Authorization': 'Bearer ' + arm_access_token,
        'Content-Type': 'application/json'
     }

    url = f'{consts.AzureResourceManager}/subscriptions/{consts.SubscriptionId}/resourceGroups/{consts.ResourceGroup}' + \
        f'/providers/Microsoft.VideoIndexer/accounts/{consts.AccountName}/generateAccessToken?api-version={consts.ApiVersion}'

    params = {
        'permissionType': permission_type,
        'scope': scope
    }
    
    if video_id is not None:
        params['videoId'] = video_id

    response = requests.post(url, json=params, headers=headers)
    
    # check if the response is valid
    response.raise_for_status()
    
    access_token = response.json().get('accessToken')

    return access_token

def get_file_name_no_extension(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def save_images_locally(local_directory: str, images: list) -> None:
    """
    Save images locally.

    :param local_directory: Directory where images (thumbnails) will be saved.
    :param images: List of PIL Image objects to save.
    """
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Save each image in the specified directory
    for idx, img in enumerate(images):
        file_path = os.path.join(local_directory, f'thumbnail_{idx}.png')
        img.save(file_path)
        print(f"Image saved at {file_path}")

class VideoIndexerClient:
    def __init__(self) -> None:
        self.arm_access_token = ''
        self.vi_access_token = ''
        self.account = None
        self.consts = None

    def get_access_token(self, consts:Consts) -> None:
        '''
        arm_access_token can be retrieved eithed from the Azure Resource Manager or 
        using Azure CLI which can generate the token for a time being, tha value can be can added to the .env file
        '''
        self.consts = consts
        # Get access tokens
        load_dotenv(find_dotenv())
        arm_access_token = os.environ.get("arm_access_token")
        if arm_access_token is None:
            self.arm_access_token = get_arm_access_token(self.consts)
        else:
            self.arm_access_token = arm_access_token
        self.vi_access_token = get_account_access_token(self.consts, self.arm_access_token)

    def get_account_initialized(self) -> None:
        '''
        Get information about the account
        '''
        if self.account is not None:
            return self.account

        headers = {
            'Authorization': 'Bearer ' + self.arm_access_token,
            'Content-Type': 'application/json'
        }

        url = f'{self.consts.AzureResourceManager}/subscriptions/{self.consts.SubscriptionId}/resourcegroups/' + \
              f'{self.consts.ResourceGroup}/providers/Microsoft.VideoIndexer/accounts/{self.consts.AccountName}' + \
              f'?api-version={self.consts.ApiVersion}'

        response = requests.get(url, headers=headers)

        response.raise_for_status()

        self.account = response.json()
        print(f'[Account Details] Id:{self.account["properties"]["accountId"]}, Location: {self.account["location"]}')

    # Upload video
    def upload_video(self, file_path:str, excluded_ai:Optional[list[str]]=None, video_name:Optional[str]=None):
        '''
        Uploads a video and starts the video index.
        
        :param file_path: url or local file path
        :param excluded_ai: The ExcludeAI list to run
        :return: Video Id of the video being indexed, otherwise throws exception
        '''
        if excluded_ai is None:
            excluded_ai = []
        
        self.get_account_initialized() # if account is not initialized, get it

        if video_name is None:
            video_name = os.path.basename(file_path)

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/Videos'

        # Check if file_path is a URL or a local path
        if bool(urlparse(file_path).scheme):  # URL
            params = {
                'accessToken': self.vi_access_token,
                'name': video_name,
                'videoUrl': file_path
            }
            if len(excluded_ai) > 0:
                params['excludedAI'] = ','.join(excluded_ai)
            response = requests.post(url, params=params)
        else:  # Local file
            if video_name is None:
                video_name = get_file_name_no_extension(file_path)
            if not os.path.exists(file_path):
                raise Exception(f'Could not find the local file {file_path}')
            params = {
                'accessToken': self.vi_access_token,
                'name': video_name[:80]  
                }
            if len(excluded_ai) > 0:
                params['excludedAI'] = ','.join(excluded_ai)
            
            print('Uploading a local file using multipart/form-data post request..')

            files = {'file': open(file_path, 'rb')}        
            response = requests.post(url, params=params, files=files)

        response.raise_for_status()

        video_id = response.json().get('id')
        print(f'Video ID {video_id} was uploaded successfully')

        return video_id
    
    def index_video(self, video_id:str, language:str='English', timeout_sec:Optional[int]=None) -> None:
        '''
        Calls getVideoIndex API in 10 second intervals until the indexing state is 'processed'
        Prints video index when the index is complete, otherwise throws exception.

        :param video_id: The video ID to wait for
        :param language: The language to translate video insights
        :param timeout_sec: The timeout in seconds
        '''
        self.get_account_initialized() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
            f'Videos/{video_id}/Index'

        params = {
            'accessToken': self.vi_access_token,
            'language': language
        }

        print(f'Checking if video {video_id} has finished indexing...')
        processing = True
        start_time = time.time()
        while processing:
            response = requests.get(url, params=params)

            response.raise_for_status()

            video_result = response.json()
            video_state = video_result.get('state')

            if video_state == 'Processed':
                processing = False
                print(f'The video index has completed. Here is the full JSON of the index for video ID {video_id}: \n{video_result}')
                break
            elif video_state == 'Failed':
                processing = False
                print(f"The video index failed for video ID {video_id}.")
                break

            print(f'The video index state is {video_state}')

            if timeout_sec is not None and time.time() - start_time > timeout_sec:
                print(f'Timeout of {timeout_sec} seconds reached. Exiting...')
                break

            time.sleep(10) # wait 10 seconds before checking again

    # Get video insights
    def get_video_insights(self, video_id:str) -> dict:
        '''
        Gets the video index. Calls the index API
        Prints the video metadata, otherwise throws an exception

        :param video_id: The video ID
        '''
        self.get_account_initialized() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
               f'Videos/{video_id}/Index'

        params = {
            'accessToken': self.vi_access_token
        }

        response = requests.get(url, params=params)

        response.raise_for_status()

        insights = response.json()
        print(f'Here are the search results: \n{insights}')
        return insights
    
    def get_video_thumbnail(self, video_id:str, thumbnail_id:str) -> None:
        '''
        Calls the Get Video Thumbnail API

        :param video_id: The video ID
        :thumbnail_id: the thumbnail ID
        '''
        self.get_account_initialized() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
               f'Videos/{video_id}/Thumbnails/{thumbnail_id}'

        params = {
            'accessToken': self.vi_access_token
        }

        response = requests.get(url, params=params)

        return response

    # Get face thumbnails from insights
    def get_face_images(self, insights:dict, video_id:str) -> list:
        """
        Retrieve face images from the video insights.

        :param insights: Dictionary containing video insights.
        :param video_id: ID of the video.
        :return: List of PIL Image objects containing the thumbnails.
        """
        images = []

        # Iterate through face thumbnails
        for each_thumb in insights['videos'][0]['insights']['faces'][0]['thumbnails']:
            if 'fileName' in each_thumb and 'id' in each_thumb:
                thumb_id = each_thumb['id']
                response = self.get_video_thumbnail(video_id, thumb_id)
                img_code = response.content  # Extract JPEG-encoded image content
                img_stream = BytesIO(img_code)
                img = Image.open(img_stream)
                images.append(img)

        return images
    
    def get_emotions_from_insights(self, insights:dict) -> None:
        """
        Extract emotions from video insights and print them.

        :param insights: Dictionary containing video insights.
        """
        emotions_data = {}
        table_data = []

        no_of_emotions = len(insights['videos'][0]['insights']['emotions'])
        print(f'{no_of_emotions} types of emotions captured in the video')

        for emotion_data in insights['videos'][0]['insights']['emotions']:
            emotion_type = emotion_data['type']
            confidence_score = emotion_data['instances'][0]['confidence']
        
            # Store emotion and confidence in the dictionary
            emotions_data[emotion_type] = confidence_score  
        
            # Append data to table for printing
            table_data.append([emotion_type, confidence_score])

        # Print table
        print(tabulate(table_data, headers=["Emotion Type", "Confidence Score"], tablefmt="pretty"))
    
        # return emotions_data

    # Get total sentiments and their duration ratios
    def get_sentiments_from_insights(self, insights:dict) -> dict:
        """
        Extract sentiments from video insights and print them in a tabular format.

        :param insights: Dictionary containing video insights.
        :return: Dictionary with sentiment keys.
        """
        sentiments_data = {}
        table_data = []

        no_of_sentiments = len(insights['summarizedInsights']['sentiments'])
        print(f'{no_of_sentiments} types of sentiments captured in the video')

        for sentiment_data in insights['summarizedInsights']['sentiments']:
            sentiment_key = sentiment_data['sentimentKey']
        
            # Store sentiment key in the dictionary
            sentiments_data[sentiment_key] = sentiment_key  
        
            # Append data to table for printing
            table_data.append([sentiment_key])

        # Print table
        # print(tabulate(table_data, headers=["Sentiment"], tablefmt="pretty"))
        # Print dictionary in list format
    
        return print(f"\nSentiments List: {list(sentiments_data.keys())}")

if __name__ == "__main__":
    # Load and define env parameters
    load_dotenv(find_dotenv())

    config = dotenv_values(".env")

    arm_access_token = config.get("arm_access_token")

    AccountName = config.get('AccountName')
    ResourceGroup = config.get('ResourceGroup')
    SubscriptionId = config.get('SubscriptionId')

    ApiVersion = config.get('ApiVersion')
    ApiEndpoint = config.get('ApiEndpoint')
    AzureResourceManager = config.get('AzureResourceManager')

    # VI_LOCATION = config.get('VIDEO_INDEXER_LOCATION')  # E.g., "trial" or "westeurope"
    # VI_ACCOUNT_ID = config.get('VIDEO_INDEXER_ACCOUNT_ID')
    # VI_API_ENDPOINT = f"{ApiEndpoint}/{VI_LOCATION}/Accounts/{VI_ACCOUNT_ID}"

    # get the video file path
    video_file_path = config.get("video_file_path")

    # create and validate consts
    consts = Consts(ApiVersion, ApiEndpoint, AzureResourceManager, AccountName, ResourceGroup, SubscriptionId)

    # Authenticate
    # create Video Indexer Client
    client = VideoIndexerClient()
    # Get access tokens (arm and Video Indexer account)
    client.get_access_token(consts)

    # Upload the video and get the video id
    video_id = client.upload_video(video_file_path)

    # index the video; this process will wait until the indexing is complete
    client.index_video(video_id)
    
    # Retrieve insights after indexing the video
    insights = client.get_video_insights(video_id)

    # Get face thumbnails
    face_images = client.get_face_images(insights, video_id)

    # Get emotions data
    emotions_data = client.get_emotions_from_insights(insights)

    # Get sentiments data
    sentiments_data = client.get_sentiments_from_insights(insights)
