from ImageGenerator import ImageGenerator
import runpod

def process_image(job):   
    try:
        generator = ImageGenerator()
        
        # Fetch inputs with default values if they are not provided
        input_image = job["input"].get("input_image", None)
        prompt = job["input"].get("prompt", "")
        edit_type = job["input"].get("edit_type", "default_edit")  # Default to "default_edit"
        strength = job["input"].get("strength", 0.9)  # Default strength
        denoise = job["input"].get("denoise", 0.35)    # Default denoise

        return generator.edit_image(input_image, prompt, edit_type, strength, denoise)
    
    except Exception as error:
        return 'error: ' + str(error)

runpod.serverless.start({"handler": process_image})