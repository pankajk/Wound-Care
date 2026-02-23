# test_gemini_simple.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

# Configure
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Test with the model
model = genai.GenerativeModel('gemini-2.5-flash-image')

# Simple text test
print("Testing text generation...")
response = model.generate_content("Say hello")
print(f"Response: {response.text}")
print("✅ Text test passed!")

# If text works, try with a simple image
print("\nTesting with a simple image...")
# Create a simple blank image
img = Image.new('RGB', (100, 100), color='red')
response = model.generate_content(["Describe this image", img])
print(f"Image response: {response.text}")
print("✅ Image test passed!")