# import libraries
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
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

def train_publish(project_id):
    # Start the training 
    iteration = trainer.train_project(project_id)
    while (iteration.status != "Completed"):
        iteration = trainer.get_iteration(project_id, iteration.id)
        print ("Training status: " + iteration.status)
        print ("Waiting 10 seconds...")
        time.sleep(10)

    # publish the model
    ## Setting the Iteration Name, this will be used when Model training is completed
    publish_iteration_name = "project1-iter1"
    # The iteration is now trained. Publish it to the project endpoint
    trainer.publish_iteration(project_id, iteration.id, publish_iteration_name, prediction_resource_id)
    print ("Done!")

    return project_id, iteration.id, publish_iteration_name

if __name__ == "__main__":
    project_id = config['custom_vision']['project_id']
    train_publish(project_id)

