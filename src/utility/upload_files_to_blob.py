# Import libraries
import os
import requests
from dotenv import dotenv_values, load_dotenv, find_dotenv
from typing import Optional, List
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import json

def upload_files_from_local(directory, connection_string, container_name):
    """
    Uploads a list of files to an Azure Blob Storage container.
    
    Parameters:
        file_paths (list): List of full file paths to upload.
        connection_string (str): Connection string to Azure Blob Storage account.
        container_name (str): Name of the Azure Blob Storage container.
    
    Returns:
        None
    """
    try:
        # Create a BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Check if the container exists, if not create it
        if not container_client.exists():
            container_client.create_container()
            print(f"Created container: {container_name}")
        
        # get file_paths from the directory
        file_paths = []
        # Iterate through directory contents
        for root, dirs, files in os.walk(directory):
            for file in files:
                # Create the full path by joining root directory with file name
                full_path = os.path.join(root, file)
                file_paths.append(full_path)
        
        # Ensure file_paths is a list, not a string
        if isinstance(file_paths, str):
            raise ValueError("file_paths should be a list of file paths, not a string.")

        # Loop through the list of file paths
        for file_path in file_paths:
            # Check if file_path is a file and not a directory
            if os.path.isfile(file_path):
                # Extract the file name from the path
                file_name = os.path.basename(file_path)

                # Get a BlobClient for the file
                blob_client = container_client.get_blob_client(file_name)

                # Open the file and upload its contents
                with open(file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
                    print(f"Uploaded {file_name} to container: {container_name}")
            else:
                print(f"Skipping directory or invalid file path: {file_path}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def upload_images_list(images, container_name, connection_string):
    """
    Upload images from the images list directly to Azure Blob Storage.

    Parameters:
        images (list): A list of PIL Image objects to be uploaded.
        container_name (str): The name of the Azure Blob Storage container.
        connection_string (str): The Azure Blob Storage connection string.

    Returns:
        None
    """
    # Initialize the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Create a BlobClient for each image
    for idx, image in enumerate(images):
        try:
            # Convert the image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()

            # Create a unique blob name (you can modify this as needed)
            blob_name = f'image_{idx}.jpg'
            
            # Get the container client
            container_client = blob_service_client.get_container_client(container_name)
            
            # Upload the image directly from memory
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(img_byte_arr)
            
            print(f"Uploaded {blob_name} successfully.")
        
        except Exception as e:
            print(f"An error occurred while uploading {blob_name}: {str(e)}")

def upload_files(file_data_list, file_names, container_name, connection_string):
    """
    Upload files (images, JSON, PDFs, etc.) to Azure Blob Storage.

    Parameters:
        file_data_list (list): A list of binary content or file-like objects.
        file_names (list): A list of file names to use for the blobs in storage (e.g., ['file1.json', 'image1.jpg']).
        container_name (str): The name of the Azure Blob Storage container.
        connection_string (str): The Azure Blob Storage connection string.

    Returns:
        None
    """
    # Initialize the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Loop through the file data and file names
    for file_data, file_name in zip(file_data_list, file_names):
        try:
            # Get the container client
            container_client = blob_service_client.get_container_client(container_name)
            
            # Create a BlobClient
            blob_client = container_client.get_blob_client(file_name)
            
            # Upload the file content to blob storage
            if isinstance(file_data, bytes):
                # If file_data is in bytes (e.g., an image or file read in binary mode)
                blob_client.upload_blob(file_data)
            elif isinstance(file_data, io.BytesIO):
                # If file_data is a BytesIO stream
                blob_client.upload_blob(file_data.getvalue())
            else:
                raise ValueError("File data must be in bytes or BytesIO format.")

            print(f"Uploaded {file_name} successfully.")
        
        except Exception as e:
            print(f"An error occurred while uploading {file_name}: {str(e)}")



# Define a utility function to upload files to Azure Blob Storage
def upload_file_to_blob(blob_service_client, container_name, file_name, file_data):
    """
    Upload any file (image, document, json, etc.) to Azure Blob Storage.
    
    Args:
    - blob_service_client: BlobServiceClient object for accessing Azure Blob.
    - container_name: Name of the container to upload to.
    - file_name: The name of the file to upload.
    - file_data: The content of the file (bytes or string).

    Returns:
    - The URL of the uploaded file.
    """
    try:
        # Get the blob client
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

        # Upload the file
        blob_client.upload_blob(file_data)
        print(f"File {file_name} uploaded successfully.")

        # Return the URL of the uploaded file
        blob_url = f"{blob_service_client.url}/{container_name}/{file_name}"
        return blob_url
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to upload images directly from a list of PIL Image objects to Blob
def upload_images_list(blob_service_client, container_name, images: List[Image.Image], file_names: List[str]):
    """
    Upload a list of images (in PIL Image format) directly to Azure Blob Storage.
    
    Args:
    - blob_service_client: The BlobServiceClient object for accessing Azure Blob Storage.
    - container_name: The name of the container in Azure Blob Storage.
    - images: List of PIL Image objects to be uploaded.
    - file_names: Corresponding file names for the images.

    Returns:
    - List of URLs of the uploaded images.
    """
    uploaded_urls = []

    for img, file_name in zip(images, file_names):
        # Save the image to a byte stream instead of a local file
        img_byte_array = BytesIO()
        img.save(img_byte_array, format='PNG')  # Save in desired format
        img_byte_array.seek(0)

        # Upload the image to blob storage
        blob_url = upload_file_to_blob(blob_service_client, container_name, file_name, img_byte_array.getvalue())
        if blob_url:
            uploaded_urls.append(blob_url)

    return uploaded_urls

# Function to upload JSON data to Azure Blob Storage
def upload_json_to_blob(blob_service_client, container_name, json_data: dict, file_name: str):
    """
    Upload a JSON file to Azure Blob Storage.
    
    Args:
    - blob_service_client: BlobServiceClient object for accessing Azure Blob.
    - container_name: Name of the container to upload to.
    - json_data: The JSON data to upload.
    - file_name: The name of the JSON file to upload.

    Returns:
    - The URL of the uploaded JSON file.
    """
    try:
        json_string = json.dumps(json_data)
        return upload_file_to_blob(blob_service_client, container_name, file_name, json_string)
    except Exception as e:
        print(f"Error uploading JSON file: {e}")
        return None

def get_files_from_directory(directory_path):
    # List to store file paths
    files_list = []
    
    # Traverse the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            # Get full file path and add it to the list
            full_file_path = os.path.join(root, file)
            files_list.append(full_file_path)
    
    return files_list

def get_files_from_blob_container(blob_service_client, container_name):
    # List to store blob (file) names
    blob_files_list = []
    
    # Get a container client
    container_client = blob_service_client.get_container_client(container_name)
    
    # List all blobs in the container
    blobs_list = container_client.list_blobs()
    
    for blob in blobs_list:
        blob_files_list.append(blob.name)
    
    return blob_files_list

def get_file_paths_from_blob_container(blob_service_client, container_name):
    # List to store blob file URLs
    blob_file_paths = []
    
    # Get a container client
    container_client = blob_service_client.get_container_client(container_name)
    
    # List all blobs in the container
    blobs_list = container_client.list_blobs()
    
    # Construct the full blob URL for each blob and append to the list
    for blob in blobs_list:
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob.name}"
        blob_file_paths.append(blob_url)
    
    return blob_file_paths

def save_thumbnails_locally(local_directory: str, images: list) -> None:
    """
    Save thumbnails locally.

    :param local_directory: Directory where thumbnails will be saved.
    :param images: List of PIL Image objects to save.
    """
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Save each image in the specified directory
    for idx, img in enumerate(images):
        file_path = os.path.join(local_directory, f'thumbnail_{idx}.png')
        img.save(file_path)
        print(f"Image saved at {file_path}")

# Example usage
if __name__ == "__main__":
    # Load and define environment variables
    load_dotenv(find_dotenv())
    config = dotenv_values(".env")
    # Azure Blob Storage configuration
    blob_service_client = BlobServiceClient(account_url=config.get('BLOB_ACCOUNT_URL'), credential=config.get('BLOB_SAS_TOKEN'))
    container_name = config.get('BLOB_CONTAINER_NAME')
    # Example image list upload
    # Suppose `images` is a list of PIL Image objects
    images = [...]  # Your list of images here
    file_names = [f"image_{i}.png" for i in range(len(images))]
    uploaded_image_urls = upload_images_list(blob_service_client, container_name, images, file_names)
    print(f"Uploaded images URLs: {uploaded_image_urls}")

    # Example JSON upload
    json_data = {
        "name": "Sample JSON",
        "description": "This is a test JSON file"
    }
    json_file_name = "sample_data.json"
    uploaded_json_url = upload_json_to_blob(blob_service_client, container_name, json_data, json_file_name)
    print(f"Uploaded JSON URL: {uploaded_json_url}")

    # Collecting Files from a Local Directory
    local_files = get_files_from_directory("/path/to/local/directory")
    print(local_files)

    # Collecting Files from Azure Blob Storage
    connection_string = "your_connection_string"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_files = get_files_from_blob_container(blob_service_client, "your-container-name")
    print(blob_files)

