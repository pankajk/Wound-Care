# app/deepskin_processor.py
import cv2
import numpy as np
import base64
from deepskin import wound_segmentation, evaluate_PWAT_score, evaluate_features
from deepskin.imgproc import get_perilesion_mask, imfill
import json
import traceback

class DeepskinProcessor:
    """Enhanced Deepskin processor that extracts full analysis data"""
    
    def __init__(self):
        print("🚀 Initializing Enhanced Deepskin Processor...")
        self.ready = True
    
    def process_image(self, image_bytes):
        """
        Complete wound analysis with all intermediate data
        
        Returns:
            Dictionary with:
            - Original image (base64)
            - Wound mask overlay
            - Peri-wound mask overlay
            - Multi-class segmentation
            - All extracted features
            - PWAT score with breakdown
        """
        try:
            # Convert bytes to image
            nparr = np.frombuffer(image_bytes, np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if bgr is None:
                return {'success': False, 'error': 'Invalid image format'}
            
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            original_b64 = self._image_to_base64(rgb)
            
            print(f"📸 Image loaded: {rgb.shape}")
            
            # STEP 1: Multi-class semantic segmentation
            print("🔬 Running multi-class segmentation...")
            try:
                segmentation = wound_segmentation(
                    img=rgb,
                    tol=0.95,
                    verbose=True
                )
                print(f"✅ Segmentation complete. Shape: {segmentation.shape}")
            except Exception as e:
                print(f"❌ Segmentation failed: {e}")
                return {'success': False, 'error': f'Segmentation failed: {str(e)}'}
            
            # Split the multi-class mask
            if len(segmentation.shape) == 3 and segmentation.shape[2] >= 2:
                wound_mask = segmentation[:, :, 0].astype(np.uint8)
                body_mask = segmentation[:, :, 1].astype(np.uint8)
                bg_mask = segmentation[:, :, 2].astype(np.uint8) if segmentation.shape[2] > 2 else np.zeros_like(wound_mask)
            else:
                wound_mask = segmentation.astype(np.uint8)
                body_mask = np.zeros_like(wound_mask)
                bg_mask = np.zeros_like(wound_mask)
            
            # STEP 2: Generate peri-wound mask
            print("🔄 Generating peri-wound mask...")
            try:
                peri_wound_mask = get_perilesion_mask(
                    mask=wound_mask, 
                    ksize=(200, 200)
                )
                
                # Refine using body mask if available
                if np.any(body_mask > 0):
                    body_plus_wound = cv2.bitwise_or(body_mask, wound_mask)
                    filled_body = imfill(body_plus_wound)
                    peri_wound_mask = cv2.bitwise_and(
                        peri_wound_mask,
                        peri_wound_mask,
                        mask=filled_body
                    )
                print(f"✅ Peri-wound mask generated")
            except Exception as e:
                print(f"⚠️ Peri-wound generation failed: {e}")
                peri_wound_mask = np.zeros_like(wound_mask)
            
            # STEP 3: Extract ALL features
            print("📊 Extracting 40+ clinical features...")
            features = {}
            try:
                # evaluate_features requires 'prefix' argument
                features = evaluate_features(
                    img=rgb,
                    mask=wound_mask,
                    prefix='wound'  # Required argument
                )
                print(f"✅ Extracted {len(features) if features else 0} features")
            except Exception as e:
                print(f"⚠️ Feature extraction error: {e}")
                traceback.print_exc()
                features = {'error': str(e)}
            
            # STEP 4: Calculate PWAT score
            print("📈 Computing PWAT score...")
            try:
                pwat_score = evaluate_PWAT_score(
                    img=rgb,
                    mask=segmentation,
                    ksize=(200, 200),
                    verbose=True
                )
                print(f"✅ PWAT score: {pwat_score:.2f}")
            except Exception as e:
                print(f"❌ PWAT calculation failed: {e}")
                pwat_score = 0.0
            
            # STEP 5: Create visualizations
            visualizations = self._create_all_visualizations(
                rgb, wound_mask, peri_wound_mask, body_mask
            )
            
            # STEP 6: Calculate wound metrics
            wound_metrics = self._calculate_wound_metrics(
                wound_mask, peri_wound_mask, rgb.shape
            )
            
            # Compile comprehensive results
            result = {
                'success': True,
                'pwat_score': float(pwat_score),
                'pwat_severity': self._get_severity_level(pwat_score),
                'wound_detected': bool(np.any(wound_mask > 0)),
                
                # Images
                'original_image': original_b64,
                'visualizations': visualizations,
                
                # Masks (as base64 images)
                'masks': {
                    'wound_mask': self._mask_to_base64(wound_mask),
                    'peri_wound_mask': self._mask_to_base64(peri_wound_mask),
                    'body_mask': self._mask_to_base64(body_mask),
                    'segmentation': self._mask_to_base64(segmentation, is_color=True)
                },
                
                # All extracted features
                'features': self._format_features(features),
                
                # Wound metrics
                'wound_metrics': wound_metrics,
                
                # Raw data for advanced analysis
                'raw': {
                    'wound_area_pixels': int(np.sum(wound_mask > 0)),
                    'peri_area_pixels': int(np.sum(peri_wound_mask > 0)),
                    'body_area_pixels': int(np.sum(body_mask > 0)),
                    'image_dimensions': {
                        'height': rgb.shape[0],
                        'width': rgb.shape[1]
                    }
                }
            }
            
            print(f"✅ Complete analysis done. PWAT: {pwat_score:.2f}")
            return result
            
        except Exception as e:
            print(f"❌ Deepskin error: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _create_all_visualizations(self, rgb, wound_mask, peri_mask, body_mask):
        """Create multiple visualization types with improved heatmap"""
        vis = {}
        
        try:
            # 1. Wound outline only (green)
            wound_outline = rgb.copy()
            contours, _ = cv2.findContours(
                wound_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(wound_outline, contours, -1, (0, 255, 0), 3)
            vis['wound_outline'] = self._image_to_base64(wound_outline)
            
            # 2. Wound + Peri-wound (green wound, blue peri-wound)
            combined = rgb.copy()
            if np.any(peri_mask > 0):
                peri_contours, _ = cv2.findContours(
                    peri_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                cv2.drawContours(combined, peri_contours, -1, (255, 0, 0), 2)  # Blue peri
            cv2.drawContours(combined, contours, -1, (0, 255, 0), 3)       # Green wound
            vis['combined_outline'] = self._image_to_base64(combined)
            
            # 3. Wound-only masked image
            wound_only = cv2.bitwise_and(rgb, rgb, mask=wound_mask)
            vis['wound_only'] = self._image_to_base64(wound_only)
            
            # 4. IMPROVED HEATMAP - Create a proper color heatmap
            # Create a colored overlay based on mask regions
            heatmap = rgb.copy().astype(np.float32)
            
            # Create different colored overlays for each region
            if np.any(wound_mask > 0):
                # Wound area - red heat
                wound_overlay = np.zeros_like(heatmap)
                wound_overlay[wound_mask > 0] = [255, 100, 100]  # Reddish
                heatmap = cv2.addWeighted(heatmap, 0.6, wound_overlay, 0.4, 0)
            
            if np.any(peri_mask > 0):
                # Peri-wound area - blue heat
                peri_overlay = np.zeros_like(heatmap)
                peri_overlay[peri_mask > 0] = [100, 100, 255]  # Bluish
                heatmap = cv2.addWeighted(heatmap, 0.6, peri_overlay, 0.4, 0)
            
            if np.any(body_mask > 0) and not np.all(body_mask == 0):
                # Body area - subtle green tint
                body_overlay = np.zeros_like(heatmap)
                body_overlay[body_mask > 0] = [100, 255, 100]  # Greenish
                heatmap = cv2.addWeighted(heatmap, 0.8, body_overlay, 0.2, 0)
            
            # Convert back to uint8
            heatmap = np.clip(heatmap, 0, 255).astype(np.uint8)
            
            # Add a color bar/legend in the image
            legend = np.zeros((60, heatmap.shape[1], 3), dtype=np.uint8)
            # Red for wound
            cv2.rectangle(legend, (10, 10), (30, 30), (0, 0, 255), -1)
            cv2.putText(legend, 'Wound', (40, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            # Blue for peri-wound
            cv2.rectangle(legend, (150, 10), (170, 30), (255, 0, 0), -1)
            cv2.putText(legend, 'Peri-wound', (180, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Combine legend with heatmap
            heatmap_with_legend = np.vstack([heatmap, legend])
            vis['heatmap'] = self._image_to_base64(heatmap_with_legend)
            
            # 5. Additional: Transparency overlay (alternative visualization)
            overlay = rgb.copy()
            alpha = 0.3
            
            # Create colored masks
            wound_color = np.zeros_like(rgb)
            wound_color[wound_mask > 0] = [255, 0, 0]  # Red for wound
            
            peri_color = np.zeros_like(rgb)
            peri_color[peri_mask > 0] = [0, 0, 255]  # Blue for peri-wound
            
            # Apply overlay
            overlay = cv2.addWeighted(overlay, 1, wound_color, alpha, 0)
            overlay = cv2.addWeighted(overlay, 1, peri_color, alpha, 0)
            
            vis['overlay'] = self._image_to_base64(overlay)
            
        except Exception as e:
            print(f"⚠️ Visualization error: {e}")
            traceback.print_exc()
        
        return vis
    
    def _calculate_wound_metrics(self, wound_mask, peri_mask, img_shape):
        """Calculate geometric wound metrics"""
        h, w = img_shape[:2]
        total_pixels = h * w
        
        wound_pixels = int(np.sum(wound_mask > 0))
        peri_pixels = int(np.sum(peri_mask > 0))
        
        # Find contours for perimeter
        contours, _ = cv2.findContours(
            wound_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if contours and len(contours) > 0:
            main_contour = max(contours, key=cv2.contourArea)
            perimeter = cv2.arcLength(main_contour, True)
            
            # Approximate diameter (assuming circular)
            if wound_pixels > 0:
                diameter = 2 * np.sqrt(wound_pixels / np.pi)
            else:
                diameter = 0
            
            # Bounding box
            x, y, box_w, box_h = cv2.boundingRect(main_contour)
        else:
            perimeter = 0
            diameter = 0
            box_w, box_h = 0, 0
            x, y = 0, 0
        
        return {
            'wound_area_pixels': wound_pixels,
            'wound_area_percentage': round((wound_pixels / total_pixels) * 100, 2) if total_pixels > 0 else 0,
            'peri_area_pixels': peri_pixels,
            'peri_area_percentage': round((peri_pixels / total_pixels) * 100, 2) if total_pixels > 0 else 0,
            'wound_perimeter_pixels': int(perimeter),
            'estimated_diameter_pixels': round(diameter, 2),
            'bounding_box': {
                'width': int(box_w),
                'height': int(box_h),
                'x': int(x),
                'y': int(y)
            }
        }
    
    def _format_features(self, features):
        """Format the 40+ features into readable categories"""
        if not features or not isinstance(features, dict):
            return {}
        
        formatted = {}
        
        # Group features by type
        texture_keys = ['contrast', 'homogeneity', 'energy', 'correlation', 'asm', 'entropy']
        color_keys = ['red', 'green', 'blue', 'hue', 'saturation', 'value', 'rgb']
        morphology_keys = ['area', 'perimeter', 'circularity', 'eccentricity', 'solidity', 'extent']
        
        categories = {
            'Texture': {},
            'Color': {},
            'Morphology': {},
            'Intensity': {},
            'Other': {}
        }
        
        for key, value in features.items():
            # Convert numpy types to Python native types
            if isinstance(value, (np.integer, int)):
                val = int(value)
            elif isinstance(value, (np.floating, float)):
                val = round(float(value), 4)
            else:
                val = str(value)
            
            # Categorize
            key_lower = key.lower()
            if any(t in key_lower for t in texture_keys):
                categories['Texture'][key] = val
            elif any(c in key_lower for c in color_keys):
                categories['Color'][key] = val
            elif any(m in key_lower for m in morphology_keys):
                categories['Morphology'][key] = val
            elif 'mean' in key_lower or 'std' in key_lower or 'intensity' in key_lower:
                categories['Intensity'][key] = val
            else:
                categories['Other'][key] = val
        
        # Remove empty categories
        formatted = {k: v for k, v in categories.items() if v}
        return formatted
    
    def _get_severity_level(self, pwat):
        """Convert PWAT to clinical severity"""
        if pwat < 8:
            return {
                'level': 'Mild', 
                'color': '#27ae60', 
                'description': 'Wound is healing well. Continue current care.'
            }
        elif pwat < 16:
            return {
                'level': 'Moderate', 
                'color': '#f39c12', 
                'description': 'Active treatment recommended. Monitor closely.'
            }
        elif pwat < 24:
            return {
                'level': 'Severe', 
                'color': '#e74c3c', 
                'description': 'Requires immediate attention. Consider specialist consult.'
            }
        else:
            return {
                'level': 'Very Severe', 
                'color': '#c0392b', 
                'description': 'Critical - seek specialist care immediately.'
            }
    
    def _image_to_base64(self, image):
        """Convert numpy image to base64 string"""
        if image is None:
            return ""
        try:
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"⚠️ Image encoding error: {e}")
            return ""
    
    def _mask_to_base64(self, mask, is_color=False):
        """Convert mask to base64 image"""
        if mask is None:
            return ""
        
        try:
            if is_color:
                # For color segmentation masks
                _, buffer = cv2.imencode('.png', mask)
            else:
                # For binary masks - normalize to 0-255
                mask_vis = (mask > 0).astype(np.uint8) * 255
                _, buffer = cv2.imencode('.png', mask_vis)
            
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"⚠️ Mask encoding error: {e}")
            return ""
    
    def get_feature_summary(self, features):
        """Generate a human-readable summary of key features"""
        if not features:
            return "No features available"
        
        summary = []
        
        # Look for key clinical indicators
        key_indicators = {
            'redness': 'Inflammation',
            'granulation': 'Healing tissue',
            'slough': 'Non-viable tissue',
            'exudate': 'Moisture level'
        }
        
        for key, value in features.items():
            key_lower = key.lower()
            for indicator, label in key_indicators.items():
                if indicator in key_lower:
                    summary.append(f"{label}: {value}")
        
        return summary if summary else "Features extracted successfully"