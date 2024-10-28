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

def create_project():
    # create a training project
    # Find the object detection domain
    domain_type = config['custom_vision']['domain_type']
    domain_name = config['custom_vision']['domain_name']
    obj_detection_domain = next(domain for domain in trainer.get_domains() if domain.type == domain_type and domain.name == domain_name)

    # Create a new project
    print ("Your Object Detection Training project has been created.")
    project_name = uuid.uuid4()
    project = trainer.create_project(project_name, domain_id=obj_detection_domain.id)

    return project.id, project_name

if __name__ == "__main__":
    create_project()