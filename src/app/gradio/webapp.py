import sys
sys.path.append('/home/mnahsan21/Udacity/Azure/automated-boarding-kiosk/src/')

import gradio as gr
from flask import Flask
from kiosk_main import main

# Flask app to run the backend
app = Flask(__name__)

# Temporary variables to store uploaded files
id_file = None
boarding_pass_file = None
video_file = None

# Functions to handle file uploads
def upload_id(id_upload):
    global id_file
    id_file = id_upload
    return "ID uploaded successfully!"

def upload_boarding_pass(bp_upload):
    global boarding_pass_file
    boarding_pass_file = bp_upload
    return "Boarding pass uploaded successfully!"

def upload_video(video_upload):
    global video_file
    video_file = video_upload
    return "Video uploaded successfully!"

# Function to validate all files
def validate():
    if id_file and boarding_pass_file and video_file:
        try:
            validation_message = main(id_file.name, boarding_pass_file.name, video_file.name)
            return validation_message
        except Exception as e:
            return f"Error during validation: {str(e)}"
    else:
        return "Please upload all files (ID, Boarding Pass, Video) to proceed."


# Gradio Interface
with gr.Blocks() as gradio_app:
    gr.Markdown("## Flight Verification Kiosk")
    
    id_output = gr.Textbox(label="ID Upload Status")
    boarding_pass_output = gr.Textbox(label="Boarding Pass Upload Status")
    video_output = gr.Textbox(label="Video Upload Status")
    
    validation_output = gr.Textbox(label="Validation Message", placeholder="Validation result will appear here")

    # Upload Buttons
    id_upload_button = gr.File(label="Upload ID", file_types=["image", ".pdf"], file_count="single")
    bp_upload_button = gr.File(label="Upload Boarding Pass", file_types=["image", ".pdf"], file_count="single")
    video_upload_button = gr.File(label="Upload Video", file_types=[".mp4", ".avi"], file_count="single")
    
    # Action Buttons
    validate_button = gr.Button("Validate")

    # Link actions to Gradio functions
    id_upload_button.upload(upload_id, inputs=id_upload_button, outputs=id_output)
    bp_upload_button.upload(upload_boarding_pass, inputs=bp_upload_button, outputs=boarding_pass_output)
    video_upload_button.upload(upload_video, inputs=video_upload_button, outputs=video_output)
    
    validate_button.click(validate, outputs=validation_output)

# Launch the app
if __name__ == "__main__":
    gradio_app.launch()
