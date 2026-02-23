# test_full.py
import requests
import json
from PIL import Image
import io
import os

# Configuration
API_URL = "http://localhost:8000"
IMAGE_PATH = "tests/test_images/0088.png"  # Update this to your image path

def test_health():
    """Test if API is running"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API Health Check: OK")
            print(f"   Deepskin: {response.json().get('deepskin', 'N/A')}")
            print(f"   Gemini: {response.json().get('gemini', 'N/A')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure the API is running with: python -m uvicorn app.main:app --reload")
        return False

def analyze_wound(image_path):
    """Send image for wound analysis"""
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    # Read image file
    with open(image_path, 'rb') as f:
        files = {'file': (os.path.basename(image_path), f, 'image/png')}
        
        try:
            # Send POST request
            response = requests.post(f"{API_URL}/analyze", files=files)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

def print_results(result):
    """Pretty print the analysis results"""
    
    print("\n" + "="*60)
    print("WOUND ANALYSIS RESULTS")
    print("="*60)
    
    if not result:
        print("❌ No results to display")
        return
    
    # Deepskin Results
    print(f"\n📊 DEEPSKIN ANALYSIS:")
    ds = result.get('deepskin', {})
    if ds.get('success'):
        print(f"   PWAT Score: {ds.get('pwat_score', 'N/A'):.2f}")
        print(f"   Wound Detected: {ds.get('wound_detected', False)}")
        print(f"   Wound Area: {ds.get('wound_area_pixels', 0)} pixels")
        print(f"   Wound Percentage: {ds.get('wound_percentage', 0):.2f}%")
    else:
        print(f"   ❌ Failed: {ds.get('error', 'Unknown error')}")
    
    # Gemini Results
    print(f"\n🧠 GEMINI ANALYSIS:")
    gem = result.get('gemini', {})
    if gem and gem.get('success'):
        print(f"   Model: {gem.get('model_used', 'unknown')}")
        print(f"   Timestamp: {gem.get('timestamp', 'N/A')}")
        print("\n   " + "-"*40)
        print(gem.get('analysis', 'No analysis text'))
        print("   " + "-"*40)
    else:
        if gem:
            print(f"   ❌ Failed: {gem.get('error', 'Unknown error')}")
            if 'note' in gem:
                print(f"   📝 Note: {gem['note']}")
        else:
            print("   ⚠️ No Gemini analysis available")
    
    # File info
    print(f"\n📁 File: {result.get('filename', 'unknown')}")
    print(f"🕒 Timestamp: {result.get('timestamp', 'N/A')}")
    
    print("\n" + "="*60)

def save_results(result, filename="analysis_result.json"):
    """Save results to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Results saved to: {filename}")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")

def main():
    """Main test function"""
    
    print("🔬 Wound Analysis API Test")
    print("="*60)
    
    # Step 1: Check if API is running
    if not test_health():
        print("\n📝 To start the API, run:")
        print("   cd C:\\dev\\wound-analysis-app\\backend")
        print("   ..\\venv\\Scripts\\activate")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # Step 2: Check if image exists
    if not os.path.exists(IMAGE_PATH):
        print(f"\n❌ Test image not found: {IMAGE_PATH}")
        print("   Please add a test image to: tests/test_images/")
        print("   You can:")
        print("   1. Copy a wound image to that folder")
        print("   2. Update IMAGE_PATH variable in this script")
        return
    
    # Step 3: Analyze wound
    print(f"\n📤 Sending image for analysis: {IMAGE_PATH}")
    print("   This may take 10-20 seconds...")
    
    result = analyze_wound(IMAGE_PATH)
    
    # Step 4: Display results
    if result:
        print_results(result)
        save_results(result)
        
        # Quick summary
        if result.get('deepskin', {}).get('success'):
            pwat = result['deepskin']['pwat_score']
            if pwat < 8:
                severity = "MILD"
            elif pwat < 16:
                severity = "MODERATE"
            elif pwat < 24:
                severity = "SEVERE"
            else:
                severity = "VERY SEVERE"
            
            print(f"\n📋 QUICK SUMMARY:")
            print(f"   PWAT Score: {pwat:.2f} - {severity}")
    else:
        print("\n❌ Analysis failed")

def batch_test(image_folder="tests/test_images/"):
    """Test multiple images in a folder"""
    
    if not os.path.exists(image_folder):
        print(f"❌ Folder not found: {image_folder}")
        return
    
    images = [f for f in os.listdir(image_folder) 
              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not images:
        print(f"❌ No images found in {image_folder}")
        return
    
    print(f"\n📸 Found {len(images)} images to test")
    
    for i, image in enumerate(images, 1):
        print(f"\n--- Testing image {i}/{len(images)}: {image} ---")
        image_path = os.path.join(image_folder, image)
        result = analyze_wound(image_path)
        
        if result and result.get('deepskin', {}).get('success'):
            pwat = result['deepskin']['pwat_score']
            print(f"   ✅ PWAT: {pwat:.2f}")
        else:
            print(f"   ❌ Failed")

if __name__ == "__main__":
    # Run main test
    main()
    
    # Uncomment to test multiple images:
    # batch_test()
    
    # Uncomment for interactive mode:
    # while True:
    #     img = input("\nEnter image path (or 'quit'): ")
    #     if img.lower() == 'quit':
    #         break
    #     IMAGE_PATH = img
    #     main()