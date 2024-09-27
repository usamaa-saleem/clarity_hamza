import json
from urllib import request, parse
import copy
import websocket
import time
import uuid
import random
import requests
import os
import cv2
import base64

class ImageGenerator():
    def __init__(self) -> None:
        self.websocket = websocket.WebSocket()
        self.connect_to_web_hook()
        
    

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = parse.urlencode(data)
        with request.urlopen("http://127.0.0.1:8188/view?{}".format(url_values)) as response:
            return response.read()
        
    
    def connect_to_web_hook(self):
        id = str(uuid.uuid4())
        while True:
            try:
                self.websocket.connect("ws://127.0.0.1:8188/ws?clientId={}".format(id))
                break
            except ConnectionRefusedError as e:
                print("Could not connect to ComfyUI because it is not up yet. Sleeping for 2 seconds before trying again.")
                time.sleep(2)

    def queue_prompt(self, prompt_workflow):
        data = {"prompt": prompt_workflow}
        data = json.dumps(data).encode('utf-8')
        req =  request.Request("http://127.0.0.1:8188/prompt", data=data)
        return json.loads(request.urlopen(req).read())
    
    def get_history(self, prompt_id):
        with request.urlopen("http://127.0.0.1:8188/history/{}".format(prompt_id)) as response:
            return json.loads(response.read())
            
    def get_images(self, prompt_id, breaking_steps):
        output_images = {}
        done_first = False
        while True:
            out = self.websocket.recv()
            if isinstance(out, str):
                message = json.loads(out)
                print(message)
                if(message['type'] == "status"):
                    if message["data"]["status"]["exec_info"]["queue_remaining"] == 1:
                        done_first = True
                    if message["data"]["status"]["exec_info"]["queue_remaining"] == 0 and done_first == True:
                        break
                if message['type'] == 'progress':
                    data = message['data']
                    if(data["max"] == breaking_steps and data["max"] == data["value"]):
                        break
                if breaking_steps == -1:
                    break
            else:
                continue
        while True:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                break
        history = history[prompt_id]
        for o in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                images_output = []
                if 'images' in node_output:
                    for image in node_output['images']:
                        image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                output_images[node_id] = images_output
        return self.convert_to_base64(output_images[node_id])

    def convert_to_base64(self, images):
        base64_encoded_str = base64.b64encode(images[0]).decode('utf-8')
        return base64_encoded_str

    def download_image(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                image_name = str(uuid.uuid4()) + ".jpg"
                file_name = os.path.join("ComfyUI/input", image_name)
                with open(file_name, 'wb') as file:
                    file.write(response.content)
                return image_name
            else:
                return ""
        except Exception as e:
            return ""

    def edit_image(self, input_image, prompt, edit_type, strength, denoise):
        settings = json.load(open('utils/config.json'))
        input_image_name = self.download_image(input_image)
        if edit_type not in settings:
            return "Invalid Model provided"
        if input_image_name == "":
            return "Invalid Input Image Provided"
        current_settings = settings[edit_type]
        workflow = json.load(open('utils/workflows/' + current_settings["workflow_file"]))

        noise_seed_nodes = current_settings["noise_seed_nodes"]
        for node in noise_seed_nodes:
            workflow[node]["inputs"]["seed"] = random.randint(1, 999999999)

        prompt_nodes = current_settings["prompt_nodes"]
        for node in prompt_nodes:
            workflow[node]["inputs"]["text"] = current_settings["prefix_prompt"] + prompt + current_settings["postfix_prompt"]


        image_input_nodes = current_settings["image_input_nodes"]
        for node in image_input_nodes:
            workflow[node]["inputs"]["image"] = input_image_name

        strength_nodes = current_settings["strength_nodes"]
        for node in strength_nodes:
            workflow[node]["inputs"]["strength"] = strength
        
        denoise_nodes = current_settings["denoise_nodes"]
        for node in denoise_nodes:
            workflow[node]["inputs"]["denoise"] = denoise

        image_data = self.queue_prompt(workflow)
        images = self.get_images(image_data['prompt_id'], current_settings["breaking_steps"])
        os.remove("ComfyUI/input/" + input_image_name)
        return images