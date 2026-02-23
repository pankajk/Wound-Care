# test_new_client.py
from google import genai
import os
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

# Initialize client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
model = 'gemini-2.5-flash-image'

# Load test image
image_path = 'tests/test_images/0088.png'
image = Image.open(image_path)

print(f"📸 Testing with image: {image_path}")
print(f"   Image mode: {image.mode}, Size: {image.size}")

# Simple test
print("\n🤔 Sending simple request...")
response = client.models.generate_content(
    model=model,
    contents=[
        "Describe this wound in one sentence",
        image
    ]
)

print(f"✅ Response: {response.text}")