# import libraries
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
from azure.cognitiveservices.vision.customvision.prediction.models import CustomVisionErrorException
from msrest.authentication import ApiKeyCredentials
import os, time, uuid, yaml
from dotenv import dotenv_values, load_dotenv, find_dotenv

# Get the absolute path of the root directory (where config.yaml is located)
root_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
# Use it to construct the path to config.yaml
config_path = os.path.join(root_dir, 'config.yaml')
# Load the config file
with open(config_path) as yaml_file:
    config = yaml.safe_load(yaml_file)

# Load and define env parameters
load_dotenv(find_dotenv())

# get credentials
ENDPOINT = config.get("VISION_TRAINING_ENDPOINT")
training_key = config.get("VISION_TRAINING_KEY")
prediction_key = config.get("VISION_PREDICTION_KEY")
prediction_resource_id = config.get("VISION_PREDICTION_RESOURCE_ID")

# Instantiate and authenticate the training and prediction clients
credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)
prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
predictor = CustomVisionPredictionClient(ENDPOINT, prediction_credentials)

def perform_prediction_on_folder(image_folder_path, project_id, publish_iteration_name, max_retries=3):
    # Check if the folder exists
    if not os.path.exists(image_folder_path):
        print(f"Error: The folder {image_folder_path} does not exist.")
        return

    # Get all image files in the folder
    image_files = [f for f in os.listdir(image_folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

    # Check if there are any image files in the folder
    if not image_files:
        print(f"No image files found in the folder: {image_folder_path}")
        return

    # Loop through each image file and perform predictions
    for image_file_name in image_files:
        image_path = os.path.join(image_folder_path, image_file_name)
        print(f"Processing image: {image_file_name}")
        
        # Implement retry logic
        for attempt in range(max_retries):
            try:
                with open(image_path, "rb") as image_contents:
                    results = predictor.detect_image(project_id, publish_iteration_name, image_contents.read())

                    # Display results where prediction probability is >= 10%
                    valid_predictions = [prediction for prediction in results.predictions if prediction.probability * 100 >= 10]
                    
                    if valid_predictions:
                        print(f"Results for {image_file_name}:")
                        for prediction in valid_predictions:
                            print(f"\t{prediction.tag_name}: {prediction.probability * 100:.2f}%")
                    else:
                        print(f"Predictions with less than 10% confidence for {image_file_name} are not shown.")
                
                # Pause between requests to stay within the rate limit (2 transactions/second)
                time.sleep(0.5)  # 500ms delay for 2 transactions/second rate

                # Break out of retry loop if successful
                break

            except CustomVisionErrorException as e:
                if "Too Many Requests" in str(e):
                    print(f"Rate limit reached, retrying after 2 seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)  # Wait 2 seconds before retrying
                else:
                    print(f"Error processing {image_file_name}: {str(e)}")
                    break

            # If we've exhausted all retries
            if attempt == max_retries - 1:
                print(f"Failed to process {image_file_name} after {max_retries} attempts.")

def main():
    image_folder_path = config['custom_vision']['folder_path']
    project_id = config['custom_vision']['project_id']
    publish_iteration_name = config['custom_vision']['publish_iteration_name']

    # detect images
    perform_prediction_on_folder(image_folder_path, project_id, publish_iteration_name)


if __name__ == "__main__":
    main()

