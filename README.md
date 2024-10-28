# AI-Powered Passenger Boarding Kiosk
## Objective
The objective of this project is to develop a computer vision and AI-based kiosk for airport operations. The kiosk will assist airline passengers in onboarding the plane without human assistance by performing various validations, including identity verification and luggage checks.
### Core Functionalities
The kiosk provides the following functionalities for airline passengers:
- ID and Boarding Pass Scanning: Passengers scan their ID card and boarding pass at the kiosk.
- Information Extraction: Passenger information is extracted from the boarding pass and verified against the ID card.
- Facial Recognition: A 10-second video is taken of the passenger, and facial recognition is performed to match the live person with the ID card.
- Prohibited Items Detection: The kiosk scans the carry-on baggage, identifies prohibited items, and prevents the passenger from boarding if any are found.
- Final Boarding Status: If all checks are successfully completed, the kiosk displays a message that the passenger is allowed to board. If there are issues, the passenger is advised to see an airline representative.
### Solution Strategy
1. Person Identity Validation
- Face Validation:
    - Uses Azure Video Indexer to detect and extract the face from the video.
    - Extract the face from the digital ID using Azure Document Intelligence.
    - Compares both faces to verify they match.
- DOB Validation:
    - Extract the date of birth from the ID using Azure Document Intelligence.
    - Verifies DOB against the manifest table.
- Name Validation:
    - Extract the passenger's name from the ID.
    - Validates the name against the manifest table.
2. Boarding Pass Validation
- Model Training: A custom model is trained to extract passenger information from boarding passes using Azure Document Intelligence.
- Manifest Validation: Extracted information is validated against the manifest.
3. Luggage Validation
- Prohibited Items Detection: A machine learning model is trained using Azure Custom Vision to identify prohibited items, such as lighters, from the baggage scan.
4. Final Boarding Message
- Once all validations are completed, a final message indicating success or failure is displayed, assisting the passenger in boarding or directing them to seek help.
### Execution
- Main Program: The kiosk_main.py file handles the entire validation process. It can be executed from src/kiosk_main.py.
- Web Application: A Gradio-based web application for the kiosk can be run from src/app/webapp.py.
- Dependencies: All dependencies are listed in requirements.txt.
- Configuration: Configurations, such as model IDs and service endpoints, can be updated in config.yaml.
- Credentials: Environment variables, including API keys, SAS tokens, and credentials, are stored in the .env file.
### Getting Started
1. Install Dependencies
`pip install -r requirements.txt`
2. Run the Main Application
`python src/kiosk_main.py`
3. Run the Web Application
`python src/app/gradio/webapp.py`

