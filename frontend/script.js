// script.js
class WoundAnalysisApp {
    constructor() {
        this.API_URL = 'http://localhost:8000';
        this.currentImage = null;
        this.analysisHistory = this.loadHistory();
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkAPIHealth();
    }

    initializeElements() {
        // DOM elements
        this.imagePreview = document.getElementById('imagePreview');
        this.imagePreviewContainer = document.getElementById('imagePreviewContainer');
        this.fileInput = document.getElementById('fileInput');
        this.cameraBtn = document.getElementById('cameraBtn');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.analyzeBtn = document.getElementById('analyzeBtn');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.resultsSection = document.getElementById('resultsSection');
        this.deepskinResults = document.getElementById('deepskinResults');
        this.geminiResults = document.getElementById('geminiResults');
        this.modelBadge = document.getElementById('modelBadge');
        this.errorMessage = document.getElementById('errorMessage');
        this.errorText = document.getElementById('errorText');
        this.historySection = document.getElementById('historySection');
        this.historyList = document.getElementById('historyList');
    }

    attachEventListeners() {
        // Camera button
        this.cameraBtn.addEventListener('click', () => {
            this.fileInput.setAttribute('capture', 'environment');
            this.fileInput.click();
        });

        // Upload button
        this.uploadBtn.addEventListener('click', () => {
            this.fileInput.removeAttribute('capture');
            this.fileInput.click();
        });

        // File input change
        this.fileInput.addEventListener('change', (e) => this.handleImageSelect(e));

        // Drag and drop
        this.imagePreviewContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.imagePreview.style.borderColor = '#667eea';
        });

        this.imagePreviewContainer.addEventListener('dragleave', () => {
            this.imagePreview.style.borderColor = '#3498db';
        });

        this.imagePreviewContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            this.imagePreview.style.borderColor = '#3498db';
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                this.handleImageFile(file);
            }
        });

        // Analyze button
        this.analyzeBtn.addEventListener('click', () => this.analyzeWound());
    }

    handleImageSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleImageFile(file);
        }
    }

    handleImageFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please select an image file');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentImage = {
                file: file,
                dataUrl: e.target.result
            };
            this.displayImagePreview(e.target.result);
            this.analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    displayImagePreview(imageUrl) {
        this.imagePreview.innerHTML = `<img src="${imageUrl}" alt="Wound image">`;
        this.imagePreview.classList.add('has-image');
    }

    async checkAPIHealth() {
        try {
            const response = await fetch(`${this.API_URL}/health`);
            if (response.ok) {
                const data = await response.json();
                console.log('API Health:', data);
            } else {
                this.showError('Cannot connect to analysis server. Make sure the API is running.');
            }
        } catch (error) {
            this.showError('Cannot connect to analysis server. Make sure the API is running.');
        }
    }

    async analyzeWound() {
        if (!this.currentImage) {
            this.showError('Please select an image first');
            return;
        }

        // Show loading
        this.loadingIndicator.classList.add('active');
        this.resultsSection.classList.remove('active');
        this.errorMessage.classList.remove('active');
        this.analyzeBtn.disabled = true;

        // Prepare form data
        const formData = new FormData();
        formData.append('file', this.currentImage.file);

        try {
            const response = await fetch(`${this.API_URL}/analyze`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const result = await response.json();
            this.displayResults(result);
            
            // Save to history
            this.saveToHistory(result);

        } catch (error) {
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.loadingIndicator.classList.remove('active');
            this.analyzeBtn.disabled = false;
        }
    }

    displayResults(result) {
        // Display Deepskin results
        this.displayDeepskinResults(result.deepskin);
        
        // Display Gemini results
        this.displayGeminiResults(result.gemini);
        
        // Show results section
        this.resultsSection.classList.add('active');
        
        // Scroll to results
        this.resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Add to script.js - inside displayResults method

displayDeepskinResults(deepskin) {
    if (!deepskin.success) {
        this.deepskinResults.innerHTML = `<div class="error">${deepskin.error}</div>`;
        return;
    }

    // Create tabs for different views
    let html = `
        <div class="analysis-tabs">
            <button class="tab-btn active" onclick="app.showTab('overview')">Overview</button>
            <button class="tab-btn" onclick="app.showTab('masks')">Masks</button>
            <button class="tab-btn" onclick="app.showTab('features')">Features</button>
            <button class="tab-btn" onclick="app.showTab('metrics')">Metrics</button>
        </div>
        
        <div id="tab-overview" class="tab-content active">
            ${this.renderOverviewTab(deepskin)}
        </div>
        
        <div id="tab-masks" class="tab-content">
            ${this.renderMasksTab(deepskin)}
        </div>
        
        <div id="tab-features" class="tab-content">
            ${this.renderFeaturesTab(deepskin)}
        </div>
        
        <div id="tab-metrics" class="tab-content">
            ${this.renderMetricsTab(deepskin)}
        </div>
    `;
    
    this.deepskinResults.innerHTML = html;
}

// Add this to your displayDeepskinResults method in script.js
// Update the visualization grid rendering

renderOverviewTab(deepskin) {
    const severity = deepskin.pwat_severity || {};
    const metrics = deepskin.wound_metrics || {};
    
    return `
        <div class="severity-banner" style="background: ${severity.color}20; border-left: 4px solid ${severity.color}">
            <h3 style="color: ${severity.color}">${severity.level}</h3>
            <p>${severity.description}</p>
        </div>
        
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">PWAT Score</div>
                <div class="metric-value">${deepskin.pwat_score.toFixed(2)}</div>
                <div class="metric-range">/32</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Wound Area</div>
                <div class="metric-value">${metrics.wound_area_pixels || 0}</div>
                <div class="metric-unit">pixels</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Wound %</div>
                <div class="metric-value">${metrics.wound_area_percentage || 0}%</div>
                <div class="metric-unit">of image</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Peri-Wound</div>
                <div class="metric-value">${metrics.peri_area_pixels || 0}</div>
                <div class="metric-unit">pixels</div>
            </div>
        </div>
        
        <div class="visualization-grid">
            <div class="viz-item">
                <h4>🔍 Original with Wound Outline</h4>
                <img src="data:image/jpeg;base64,${deepskin.visualizations?.wound_outline}" 
                     onclick="app.openImageModal(this.src)"
                     alt="Wound outline">
            </div>
            
            <div class="viz-item">
                <h4>🔄 Wound + Peri-Wound</h4>
                <img src="data:image/jpeg;base64,${deepskin.visualizations?.combined_outline}"
                     onclick="app.openImageModal(this.src)"
                     alt="Combined outline">
            </div>
            
            <div class="viz-item">
                <h4>🎯 Wound Only</h4>
                <img src="data:image/jpeg;base64,${deepskin.visualizations?.wound_only}"
                     onclick="app.openImageModal(this.src)"
                     alt="Wound only">
            </div>
            
            <div class="viz-item">
                <h4>🔥 Heatmap View</h4>
                <img src="data:image/jpeg;base64,${deepskin.visualizations?.heatmap}"
                     onclick="app.openImageModal(this.src)"
                     alt="Heatmap">
                <div class="heatmap-legend">
                    <div class="legend-item">
                        <span class="legend-color wound"></span>
                        <span>Wound</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color peri"></span>
                        <span>Peri-wound</span>
                    </div>
                </div>
            </div>
            
            <div class="viz-item">
                <h4>🌈 Transparency Overlay</h4>
                <img src="data:image/jpeg;base64,${deepskin.visualizations?.overlay}"
                     onclick="app.openImageModal(this.src)"
                     alt="Overlay">
            </div>
        </div>
    `;
}
renderMasksTab(deepskin) {
    return `
        <div class="masks-grid">
            <div class="mask-item">
                <h4>Wound Mask</h4>
                <img src="data:image/png;base64,${deepskin.masks?.wound_mask}">
                <p>Binary mask of wound area</p>
            </div>
            
            <div class="mask-item">
                <h4>Peri-Wound Mask</h4>
                <img src="data:image/png;base64,${deepskin.masks?.peri_wound_mask}">
                <p>Surrounding tissue area</p>
            </div>
            
            <div class="mask-item">
                <h4>Body Mask</h4>
                <img src="data:image/png;base64,${deepskin.masks?.body_mask}">
                <p>Patient body ROI</p>
            </div>
            
            <div class="mask-item">
                <h4>Multi-Class Segmentation</h4>
                <img src="data:image/png;base64,${deepskin.masks?.segmentation}">
                <p>Green: Wound | Blue: Body | Gray: Background</p>
            </div>
        </div>
    `;
}

renderFeaturesTab(deepskin) {
    const features = deepskin.features || {};
    const featureCategories = this.groupFeaturesByCategory(features);
    
    let html = '<div class="features-container">';
    
    for (const [category, items] of Object.entries(featureCategories)) {
        html += `
            <div class="feature-category">
                <h4>${category}</h4>
                <div class="feature-grid">
        `;
        
        for (const [name, value] of Object.entries(items)) {
            html += `
                <div class="feature-item">
                    <span class="feature-name">${name}:</span>
                    <span class="feature-value">${value}</span>
                </div>
            `;
        }
        
        html += '</div></div>';
    }
    
    html += '</div>';
    return html;
}

renderMetricsTab(deepskin) {
    const m = deepskin.wound_metrics || {};
    const raw = deepskin.raw || {};
    
    return `
        <div class="metrics-detailed">
            <h4>Geometric Measurements</h4>
            <table class="metrics-table">
                <tr>
                    <td>Wound Area (pixels):</td>
                    <td><strong>${m.wound_area_pixels}</strong></td>
                    <td>${m.wound_area_percentage}% of image</td>
                </tr>
                <tr>
                    <td>Peri-Wound Area:</td>
                    <td><strong>${m.peri_area_pixels}</strong></td>
                    <td>${m.peri_area_percentage}% of image</td>
                </tr>
                <tr>
                    <td>Wound Perimeter:</td>
                    <td><strong>${m.wound_perimeter_pixels}</strong></td>
                    <td>pixels</td>
                </tr>
                <tr>
                    <td>Estimated Diameter:</td>
                    <td><strong>${m.estimated_diameter_pixels}</strong></td>
                    <td>pixels (circular approximation)</td>
                </tr>
                <tr>
                    <td>Bounding Box:</td>
                    <td><strong>${m.bounding_box?.width} x ${m.bounding_box?.height}</strong></td>
                    <td>pixels</td>
                </tr>
            </table>
            
            <h4 style="margin-top: 24px;">Raw Data</h4>
            <table class="metrics-table">
                <tr><td>Image Dimensions:</td><td>${raw.image_dimensions?.width} x ${raw.image_dimensions?.height}</td></tr>
                <tr><td>Body Area:</td><td>${raw.body_area_pixels} pixels</td></tr>
                <tr><td>Wound/Body Ratio:</td><td>${(raw.wound_area_pixels / raw.body_area_pixels * 100).toFixed(2)}%</td></tr>
            </table>
        </div>
    `;
}

groupFeaturesByCategory(features) {
    // Group the 40+ features into logical categories [citation:2]
    const categories = {
        'Texture': {},
        'Color': {},
        'Morphology': {},
        'Intensity': {},
        'Other': {}
    };
    
    for (const [key, value] of Object.entries(features)) {
        if (key.includes('texture') || key.includes('contrast') || key.includes('homogeneity')) {
            categories['Texture'][key] = value;
        } else if (key.includes('color') || key.includes('rgb') || key.includes('hue')) {
            categories['Color'][key] = value;
        } else if (key.includes('area') || key.includes('perimeter') || key.includes('shape')) {
            categories['Morphology'][key] = value;
        } else if (key.includes('intensity') || key.includes('mean') || key.includes('std')) {
            categories['Intensity'][key] = value;
        } else {
            categories['Other'][key] = value;
        }
    }
    
    return categories;
}

showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // Activate button
    event.target.classList.add('active');
}

openImageModal(src) {
    // Create modal for image zoom
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <img src="${src}">
        </div>
    `;
    document.body.appendChild(modal);
}

    displayGeminiResults(gemini) {
        if (!gemini || !gemini.success) {
            this.geminiResults.innerHTML = `
                <div style="color: #e74c3c; padding: 16px; text-align: center;">
                    <i class="fas fa-exclamation-circle" style="font-size: 32px; margin-bottom: 8px;"></i>
                    <p>${gemini?.error || 'Gemini analysis not available'}</p>
                    ${gemini?.note ? `<small>${gemini.note}</small>` : ''}
                </div>
            `;
            return;
        }

        // Set model badge
        this.modelBadge.textContent = gemini.model_used;

        // Format the analysis text (convert markdown-like syntax to HTML)
        let formattedText = gemini.analysis
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        this.geminiResults.innerHTML = `
            <div class="analysis-text">
                <p>${formattedText}</p>
            </div>
            ${gemini.timestamp ? `
                <div style="margin-top: 16px; font-size: 12px; color: #666; text-align: right;">
                    <i class="far fa-clock"></i> ${new Date(gemini.timestamp).toLocaleString()}
                </div>
            ` : ''}
        `;
    }

    showError(message) {
        this.errorText.textContent = message;
        this.errorMessage.classList.add('active');
        setTimeout(() => {
            this.errorMessage.classList.remove('active');
        }, 5000);
    }

    saveToHistory(result) {
        const historyItem = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            image: this.currentImage.dataUrl,
            pwat_score: result.deepskin.pwat_score,
            severity: this.getSeverityText(result.deepskin.pwat_score)
        };

        this.analysisHistory.unshift(historyItem);
        if (this.analysisHistory.length > 10) {
            this.analysisHistory.pop();
        }

        localStorage.setItem('woundAnalysisHistory', JSON.stringify(this.analysisHistory));
        this.displayHistory();
    }

    loadHistory() {
        const saved = localStorage.getItem('woundAnalysisHistory');
        return saved ? JSON.parse(saved) : [];
    }

    getSeverityText(pwat) {
        if (pwat < 8) return 'Mild';
        if (pwat < 16) return 'Moderate';
        if (pwat < 24) return 'Severe';
        return 'Very Severe';
    }

    displayHistory() {
        if (this.analysisHistory.length === 0) {
            this.historySection.style.display = 'none';
            return;
        }

        this.historySection.style.display = 'block';
        this.historyList.innerHTML = this.analysisHistory.map(item => `
            <div class="history-item" onclick="app.loadHistoryItem(${item.id})">
                <img src="${item.image}" alt="Wound">
                <div class="history-item-info">
                    <div class="history-item-date">${new Date(item.timestamp).toLocaleDateString()}</div>
                    <div class="history-item-pwat">PWAT: ${item.pwat_score.toFixed(2)} - ${item.severity}</div>
                </div>
            </div>
        `).join('');
    }

    loadHistoryItem(id) {
        const item = this.analysisHistory.find(i => i.id === id);
        if (item) {
            this.displayImagePreview(item.image);
            // You could also re-run analysis or show previous results
        }
    }
}

// Initialize the app
const app = new WoundAnalysisApp();