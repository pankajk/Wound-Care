# backend/tests/simple_test.py
import requests

# Test health endpoint
response = requests.get("http://localhost:8000/health")
print("Health check:", response.json())
print("\n✅ API is ready!")
print("To test with an image, run:")
print('python -c "import requests; requests.post(\'http://localhost:8000/analyze\', files={\'file\': open(\'tests/test_images/your_wound.jpg\',\'rb\')})"')