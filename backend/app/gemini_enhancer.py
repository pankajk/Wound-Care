# app/gemini_enhancer.py
import os
from google import genai
from google.genai import types
from PIL import Image
import io
import base64
from datetime import datetime
import traceback

class GeminiEnhancer:
    """Adds clinical analysis using Gemini vision model with multiple fallback strategies"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.available = False
        self.client = None
        self.model_name = None
        self.fallback_models = [
            'gemini-2.5-flash-image',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro-vision'
        ]
        
        if not self.api_key:
            print("⚠️ No Google API key found. Set GOOGLE_API_KEY in .env file")
            return
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client and find working model"""
        try:
            # Initialize client
            self.client = genai.Client(api_key=self.api_key)
            print("✅ Gemini client initialized")
            
            # Try to find a working model
            for model_name in self.fallback_models:
                try:
                    print(f"🔄 Testing model: {model_name}")
                    # Simple test to see if model works
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents="test"
                    )
                    self.model_name = model_name
                    self.available = True
                    print(f"✅ Using model: {model_name}")
                    return
                except Exception as e:
                    print(f"   Model {model_name} failed: {str(e)[:50]}...")
                    continue
            
            print("❌ No working model found")
            
        except Exception as e:
            print(f"❌ Gemini initialization failed: {e}")
            traceback.print_exc()
    
    def analyze_wound(self, image_bytes, deepskin_results):
        """
        Send image to Gemini for clinical analysis with multiple fallback strategies
        
        Args:
            image_bytes: Raw image bytes
            deepskin_results: Results from Deepskin analysis
            
        Returns:
            Dictionary with analysis results or error information
        """
        if not self.available or not self.client or not self.model_name:
            return {
                'success': False,
                'error': 'Gemini not available',
                'note': 'Check API key and model access',
                'available_models': self.fallback_models
            }
        
        # Strategy 1: Standard approach with bytes
        result = self._analyze_with_bytes(image_bytes, deepskin_results)
        if result['success']:
            return result
        
        # Strategy 2: Try with PIL image directly
        result = self._analyze_with_pil(image_bytes, deepskin_results)
        if result['success']:
            return result
        
        # Strategy 3: Simple prompt without Deepskin context
        result = self._analyze_simple(image_bytes)
        if result['success']:
            return result
        
        # All strategies failed
        return {
            'success': False,
            'error': 'All analysis strategies failed',
            'details': result.get('error', 'Unknown error')
        }
    
    def _analyze_with_bytes(self, image_bytes, deepskin_results):
        """Strategy 1: Send image as bytes with full context"""
        try:
            # Open and prepare image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize large images to avoid API limits
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to bytes with optimal quality
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            img_bytes = img_byte_arr.getvalue()
            
            print(f"📸 Image prepared: {image.size}, {len(img_bytes)/1024:.1f}KB")
            
            # Extract Deepskin results
            pwat = deepskin_results.get('pwat_score', 'N/A')
            if pwat != 'N/A':
                pwat = float(pwat)
            
            wound_area = deepskin_results.get('wound_area_pixels', 0)
            wound_detected = deepskin_results.get('wound_detected', False)
            severity = deepskin_results.get('pwat_severity', {}).get('level', 'Unknown')
            
            # Create comprehensive prompt
            prompt = self._create_analysis_prompt(pwat, wound_area, wound_detected, severity)
            
            print(f"🤔 Sending to Gemini ({self.model_name}) - Strategy 1...")
            
            # Generate content with proper typing
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type="image/jpeg"
                    )
                ]
            )
            
            # Extract text response
            if hasattr(response, 'text'):
                analysis_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                analysis_text = response.candidates[0].content.parts[0].text
            else:
                analysis_text = str(response)
            
            print("✅ Received Gemini analysis")
            
            return {
                'success': True,
                'analysis': analysis_text,
                'model_used': self.model_name,
                'strategy': 'bytes',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Strategy 1 failed: {e}")
            return {'success': False, 'error': str(e), 'strategy': 'bytes'}
    
    def _analyze_with_pil(self, image_bytes, deepskin_results):
        """Strategy 2: Send PIL image directly"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            pwat = deepskin_results.get('pwat_score', 'N/A')
            severity = deepskin_results.get('pwat_severity', {}).get('level', 'Unknown')
            
            # Simpler prompt for this strategy
            prompt = f"""Analyze this wound image. 
            PWAT Score: {pwat} (0-32, higher = more severe)
            Severity: {severity}
            
            Describe the tissue composition and wound characteristics briefly."""
            
            print(f"🤔 Sending to Gemini ({self.model_name}) - Strategy 2...")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image]
            )
            
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'success': True,
                'analysis': analysis_text,
                'model_used': self.model_name,
                'strategy': 'pil',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Strategy 2 failed: {e}")
            return {'success': False, 'error': str(e), 'strategy': 'pil'}
    
    def _analyze_simple(self, image_bytes):
        """Strategy 3: Minimal prompt without Deepskin context"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Simple prompt
            prompt = "Describe this wound image. What do you see?"
            
            print(f"🤔 Sending to Gemini ({self.model_name}) - Strategy 3...")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image]
            )
            
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'success': True,
                'analysis': analysis_text,
                'model_used': self.model_name,
                'strategy': 'simple',
                'timestamp': datetime.now().isoformat(),
                'note': 'Analysis without Deepskin context'
            }
            
        except Exception as e:
            print(f"❌ Strategy 3 failed: {e}")
            return {'success': False, 'error': str(e), 'strategy': 'simple'}
    
    def _create_analysis_prompt(self, pwat, wound_area, wound_detected, severity):
        """Create a detailed clinical prompt for wound analysis"""
        
        pwat_text = f"{pwat:.2f}" if isinstance(pwat, float) else str(pwat)
        
        prompt = f"""You are a wound care specialist. Analyze this wound image and provide a detailed clinical assessment.

AUTOMATED MEASUREMENTS:
- PWAT Score: {pwat_text} (Pressure Ulcer Scale for Healing, 0-32, higher = more severe)
- Wound Area: {wound_area} pixels
- Wound Detected: {wound_detected}
- Severity Level: {severity}

Please provide a structured analysis with these sections:

1. **TISSUE COMPOSITION** (estimate percentages):
   - Granulation tissue (red, healthy tissue)
   - Slough (yellow/white, stringy tissue)
   - Necrotic/Eschar (black/brown, dead tissue)
   - Epithelialization (pink, new skin growth)

2. **WOUND BED CHARACTERISTICS**:
   - Color description
   - Moisture/exudate level (dry, moist, wet)
   - Any visible signs of infection (erythema, purulence, odor)
   - Peri-wound skin condition

3. **HEALING ASSESSMENT**:
   - What phase of healing? (inflammatory, proliferative, remodeling)
   - Is the wound improving, stable, or deteriorating based on appearance?
   - Does the automated severity ({severity}) match your visual assessment?

4. **CLINICAL RECOMMENDATIONS**:
   - Suggested dressing types based on tissue composition
   - Care instructions for patient
   - When to seek medical attention (red flags)

5. **PATIENT-FRIENDLY SUMMARY**:
   - Simple explanation in plain language
   - Easy-to-follow care steps

Keep the analysis concise but clinically relevant. Use bullet points for readability."""
        
        return prompt
    
    def analyze_with_history(self, image_bytes, deepskin_results, previous_analyses=None):
        """
        Enhanced analysis with historical comparison
        
        Args:
            image_bytes: Current image
            deepskin_results: Current Deepskin results
            previous_analyses: List of previous analysis results
            
        Returns:
            Analysis with healing trend information
        """
        if not self.available:
            return self.analyze_wound(image_bytes, deepskin_results)
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Prepare context
            current_pwat = deepskin_results.get('pwat_score', 'N/A')
            
            prompt = f"""You are a wound care specialist reviewing healing progress.

CURRENT MEASUREMENTS:
- PWAT Score: {current_pwat}
"""

            if previous_analyses and len(previous_analyses) > 0:
                prompt += "\nPREVIOUS MEASUREMENTS:\n"
                for i, prev in enumerate(previous_analyses[-3:], 1):  # Last 3 analyses
                    prev_pwat = prev.get('pwat_score', 'N/A')
                    prev_date = prev.get('timestamp', 'Unknown date')[:10]
                    prompt += f"- Analysis {i} ({prev_date}): PWAT {prev_pwat}\n"
                
                prompt += "\nBased on this trend, is the wound healing, stable, or worsening?"
            else:
                prompt += "\nThis is the first analysis - provide baseline assessment."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image]
            )
            
            analysis_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                'success': True,
                'analysis': analysis_text,
                'model_used': self.model_name,
                'with_history': bool(previous_analyses),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ History analysis failed: {e}")
            return self.analyze_wound(image_bytes, deepskin_results)
    
    def test_connection(self):
        """Simple test to verify Gemini is working"""
        if not self.available or not self.client:
            return {
                'success': False,
                'error': 'Gemini not initialized'
            }
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Say 'Gemini is working' if you can read this."
            )
            
            return {
                'success': True,
                'message': response.text if hasattr(response, 'text') else 'Working',
                'model': self.model_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model_tried': self.model_name
            }
    
    def list_available_models(self):
        """List all available models for debugging"""
        if not self.client:
            return {'success': False, 'error': 'Client not initialized'}
        
        try:
            models = self.client.models.list()
            available = []
            
            for model in models:
                if 'generateContent' in str(model.supported_actions):
                    available.append({
                        'name': model.name,
                        'display_name': getattr(model, 'display_name', 'N/A')
                    })
            
            return {
                'success': True,
                'models': available,
                'count': len(available)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }