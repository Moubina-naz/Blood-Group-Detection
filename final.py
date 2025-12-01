#YASHXOXO
import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QTextEdit, QMessageBox, QProgressBar, QTabWidget)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import skimage.io as ski
import skimage.filters as skif
import skimage.color as skic
import skimage.morphology as skim
import skimage.measure as skimeas
import skimage.feature as skifeat
import skimage.segmentation as skiseg
import skimage.exposure as skiexp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap
import warnings
warnings.filterwarnings('ignore')

class AnalysisThread(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    
    def __init__(self, fingerprint_path, blood_sample_path):
        super().__init__()
        self.fingerprint_path = fingerprint_path
        self.blood_sample_path = blood_sample_path
        
    def run(self):
        try:
            # Process fingerprint
            self.progress.emit(10)
            fingerprint_result = self.process_fingerprint(self.fingerprint_path)
            
            # Process blood sample
            self.progress.emit(30)
            blood_group, confidence, analysis_data = self.process_blood_sample(self.blood_sample_path)
            
            # Prepare results
            results = {
                'fingerprint': fingerprint_result,
                'blood_group': blood_group,
                'confidence': confidence,
                'analysis_data': analysis_data
            }
            
            self.progress.emit(100)
            self.result.emit(results)
            
        except Exception as e:
            self.result.emit({'error': str(e)})
    
    def process_fingerprint(self, image_path):
        # Enhanced fingerprint processing
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return "Invalid fingerprint image"
            
        # Basic fingerprint validation
        img_std = np.std(img)
        if img_std < 20:  # Low contrast image
            return "Low quality fingerprint"
            
        # Minutiae extraction simulation (simplified)
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Use morphological operations instead of ximgproc.thinning
        # Create a kernel for morphological operations
        kernel = np.ones((3, 3), np.uint8)
        
        # Apply erosion to thin the ridges
        ridges = cv2.erode(binary, kernel, iterations=1)
        
        # Count ridge endings and bifurcations (simplified)
        minutiae_count = np.sum(ridges == 255) // 100  # Approximation
        
        if minutiae_count > 20:
            return "Verified (High Quality)"
        elif minutiae_count > 10:
            return "Verified (Medium Quality)"
        else:
            return "Low quality fingerprint"
    
    def process_blood_sample(self, image_path):
        # Read and preprocess image
        img = ski.imread(image_path)
        if len(img.shape) == 3:
            img_gray = skic.rgb2gray(img)
            # Extract green channel for better contrast with blood cells
            img_green = img[:, :, 1]
        else:
            img_gray = img
            img_green = img
            
        # Enhanced preprocessing
        img_processed = self.enhance_blood_image(img_green)
        
        # Multiple analysis techniques
        results = []
        confidence_scores = []
        intermediate_images = {}  # Store intermediate images for visualization
        
        # Method 1: Agglutination pattern analysis
        agglutination_result, agglutination_confidence, agglutination_images = self.analyze_agglutination_patterns(img_processed)
        results.append(agglutination_result)
        confidence_scores.append(agglutination_confidence)
        intermediate_images['agglutination'] = agglutination_images
        
        # Method 2: Cell distribution analysis
        distribution_result, distribution_confidence, distribution_images = self.analyze_cell_distribution(img_processed)
        results.append(distribution_result)
        confidence_scores.append(distribution_confidence)
        intermediate_images['distribution'] = distribution_images
        
        # Method 3: Color-based analysis
        color_result, color_confidence, color_images = self.analyze_blood_color(img)
        results.append(color_result)
        confidence_scores.append(color_confidence)
        intermediate_images['color'] = color_images
        
        # Method 4: Texture analysis (new)
        texture_result, texture_confidence, texture_images = self.analyze_texture(img_processed)
        results.append(texture_result)
        confidence_scores.append(texture_confidence)
        intermediate_images['texture'] = texture_images
        
        # Combine results
        final_result, final_confidence = self.combine_analyses(results, confidence_scores)
        
        # Prepare analysis data for display
        analysis_data = {
            'methods': ['Agglutination', 'Distribution', 'Color', 'Texture'],
            'results': results,
            'confidences': confidence_scores,
            'final_result': final_result,
            'final_confidence': final_confidence,
            'intermediate_images': intermediate_images
        }
        
        return final_result, final_confidence, analysis_data
    
    def enhance_blood_image(self, img):
        # Contrast stretching
        p2, p98 = np.percentile(img, (2, 98))
        img_contrast = skiexp.rescale_intensity(img, in_range=(p2, p98))
        
        # Noise reduction
        img_denoised = skif.median(img_contrast, skim.disk(1))
        
        # Adaptive histogram equalization
        img_adaptive = skiexp.equalize_adapthist(img_denoised, clip_limit=0.03)
        
        return img_adaptive
    
    def analyze_agglutination_patterns(self, img):
        # Thresholding
        thresh = skif.threshold_otsu(img)
        binary = img > thresh
        
        # Remove small objects
        cleaned = skim.remove_small_objects(binary, min_size=50)
        cleaned = skim.remove_small_holes(cleaned, area_threshold=15)
        
        # Label regions
        labeled = skim.label(cleaned)
        regions = skimeas.regionprops(labeled)
        
        # Calculate features
        num_regions = len(regions)
        if num_regions == 0:
            return "Inconclusive", 0.0, {}
            
        areas = [r.area for r in regions]
        avg_area = np.mean(areas)
        area_std = np.std(areas)
        
        # Calculate circularity of regions
        circularities = []
        for r in regions:
            perimeter = r.perimeter
            if perimeter > 0:
                circularity = 4 * np.pi * r.area / (perimeter ** 2)
                circularities.append(circularity)
        avg_circularity = np.mean(circularities) if circularities else 0
        
        # Agglutination detection logic (enhanced)
        if num_regions < 10 and avg_area > 100 and avg_circularity < 0.7:
            # Few large, irregular clumps suggest agglutination (positive reaction)
            blood_group = "A+"
            confidence = min(0.95, 0.7 + (avg_area / 1000) + (0.7 - avg_circularity))
        elif num_regions > 50 and avg_area < 30 and avg_circularity > 0.8:
            # Many small, circular cells suggest no agglutination (negative reaction)
            blood_group = "O+"
            confidence = min(0.95, 0.7 + (50 / num_regions) + (avg_circularity - 0.5))
        else:
            # Intermediate case
            blood_group = "B+"
            confidence = 0.6
            
        # Store intermediate images
        intermediate_images = {
            'binary': binary,
            'cleaned': cleaned,
            'labeled': labeled
        }
            
        return blood_group, confidence, intermediate_images
    
    def analyze_cell_distribution(self, img):
        # Edge detection to find cell boundaries
        edges = skifeat.canny(img, sigma=1.0)
        
        # Distance transform to find cell centers
        distance = skif.sobel(img)
        
        # Find local maxima as cell centers
        coordinates = skifeat.peak_local_max(
            distance, 
            min_distance=7, 
            threshold_abs=0.1
        )
        
        num_cells = len(coordinates)
        
        # Calculate spatial distribution metrics
        if num_cells > 1:
            # Calculate pairwise distances between cells
            from scipy.spatial.distance import pdist
            distances = pdist(coordinates)
            avg_distance = np.mean(distances)
            distance_std = np.std(distances)
            
            # Uniformity measure (lower std means more uniform distribution)
            uniformity = 1.0 / (1.0 + distance_std)
        else:
            avg_distance = 0
            uniformity = 0
        
        # Analyze distribution pattern (enhanced)
        if num_cells < 20:
            blood_group = "AB+"
            confidence = 0.75
        elif num_cells > 100:
            blood_group = "O-"
            confidence = 0.8
        else:
            if uniformity > 0.7:
                blood_group = "A-"
                confidence = 0.75
            else:
                blood_group = "B-"
                confidence = 0.65
            
        # Store intermediate images
        intermediate_images = {
            'edges': edges,
            'distance': distance,
            'coordinates': coordinates
        }
            
        return blood_group, confidence, intermediate_images
    
    def analyze_blood_color(self, img):
        if len(img.shape) != 3:
            return "Inconclusive", 0.0, {}
            
        # Convert to different color spaces for analysis
        img_hsv = skic.rgb2hsv(img)
        img_lab = skic.rgb2lab(img)
        
        # Extract channels
        hue = img_hsv[:, :, 0]
        saturation = img_hsv[:, :, 1]
        value = img_hsv[:, :, 2]
        
        # Extract Lab channels
        l_channel = img_lab[:, :, 0]
        a_channel = img_lab[:, :, 1]
        b_channel = img_lab[:, :, 2]
        
        # Calculate statistics
        avg_hue = np.mean(hue)
        avg_saturation = np.mean(saturation)
        avg_value = np.mean(value)
        
        avg_a = np.mean(a_channel)
        avg_b = np.mean(b_channel)
        
        # Determine blood group based on color characteristics (enhanced)
        if avg_saturation > 0.5:
            if avg_hue < 0.05 or avg_hue > 0.9:  # Red tones
                if avg_a > 5:  # More red in Lab space
                    blood_group = "A+"
                    confidence = 0.85
                else:
                    blood_group = "A-"
                    confidence = 0.8
            else:
                if avg_b > 0:  # More yellow in Lab space
                    blood_group = "B+"
                    confidence = 0.75
                else:
                    blood_group = "B-"
                    confidence = 0.7
        else:
            if avg_hue < 0.1:  # Very red
                if avg_value > 0.6:  # Bright
                    blood_group = "O+"
                    confidence = 0.8
                else:
                    blood_group = "O-"
                    confidence = 0.75
            else:
                blood_group = "AB+"
                confidence = 0.65
                
        # Store intermediate images
        intermediate_images = {
            'hue': hue,
            'saturation': saturation,
            'value': value,
            'a_channel': a_channel,
            'b_channel': b_channel
        }
            
        return blood_group, confidence, intermediate_images
    
    def analyze_texture(self, img):
        # Compute Local Binary Pattern (LBP)
        radius = 3
        n_points = 8 * radius
        lbp = skifeat.local_binary_pattern(img, n_points, radius, method='uniform')
        
        # Compute LBP histogram
        hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
        hist = hist.astype("float")
        hist /= (hist.sum() + 1e-7)  # Normalize
        
        # Calculate texture features
        uniformity = np.sum(hist ** 2)  # Higher for more uniform textures
        entropy = -np.sum(hist * np.log2(hist + 1e-7))  # Higher for more complex textures
        
        # Texture analysis logic
        if uniformity > 0.4 and entropy < 3.0:
            # Uniform texture suggests agglutination
            blood_group = "A+"
            confidence = 0.75
        elif uniformity < 0.2 and entropy > 4.0:
            # Complex texture suggests no agglutination
            blood_group = "O+"
            confidence = 0.8
        else:
            # Intermediate texture
            if entropy > 3.5:
                blood_group = "B+"
                confidence = 0.7
            else:
                blood_group = "AB+"
                confidence = 0.65
                
        # Store intermediate images
        intermediate_images = {
            'lbp': lbp,
            'hist': hist
        }
            
        return blood_group, confidence, intermediate_images
    
    def combine_analyses(self, results, confidences):
        # Weighted voting system with enhanced weighting
        blood_groups = {}
        weights = [1.2, 1.0, 0.8, 0.7]  # Weights for each method
        
        for result, confidence, weight in zip(results, confidences, weights):
            weighted_confidence = confidence * weight
            if result in blood_groups:
                blood_groups[result] += weighted_confidence
            else:
                blood_groups[result] = weighted_confidence
        
        # Find the result with highest confidence
        best_result = max(blood_groups, key=blood_groups.get)
        total_weight = sum(weights)
        total_confidence = blood_groups[best_result] / total_weight
        
        return best_result, total_confidence


class BloodGroupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process_btn = None  # Initialize process_btn
        self.initUI()
        self.fingerprint_path = None
        self.blood_sample_path = None
        
    def initUI(self):
        self.setWindowTitle('Advanced Blood Group Identification System')
        self.setGeometry(100, 100, 1200, 900)
        
        # Set a standard font to avoid warnings
        font = QFont("Arial", 11)
        QApplication.setFont(font)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title = QLabel('Advanced Blood Group Identification System')
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Image upload section
        upload_group = QGroupBox("Upload Images")
        upload_layout = QHBoxLayout()
        
        # Fingerprint upload
        fingerprint_box = QVBoxLayout()
        self.fingerprint_label = QLabel('Fingerprint Image')
        self.fingerprint_label.setAlignment(Qt.AlignCenter)
        self.fingerprint_label.setMinimumSize(300, 200)
        self.fingerprint_label.setStyleSheet("border: 1px solid gray;")
        fingerprint_btn = QPushButton('Upload Fingerprint')
        fingerprint_btn.clicked.connect(self.upload_fingerprint)
        fingerprint_box.addWidget(self.fingerprint_label)
        fingerprint_box.addWidget(fingerprint_btn)
        
        # Blood sample upload
        blood_box = QVBoxLayout()
        self.blood_label = QLabel('Blood Sample Image')
        self.blood_label.setAlignment(Qt.AlignCenter)
        self.blood_label.setMinimumSize(300, 200)
        self.blood_label.setStyleSheet("border: 1px solid gray;")
        blood_btn = QPushButton('Upload Blood Sample')
        blood_btn.clicked.connect(self.upload_blood_sample)
        blood_box.addWidget(self.blood_label)
        blood_box.addWidget(blood_btn)
        
        upload_layout.addLayout(fingerprint_box)
        upload_layout.addLayout(blood_box)
        upload_group.setLayout(upload_layout)
        main_layout.addWidget(upload_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Process button - store reference to this button
        self.process_btn = QPushButton('Analyze Blood Group')
        self.process_btn.clicked.connect(self.analyze_blood_group)
        self.process_btn.setStyleSheet("font-size: 16px; padding: 10px;")
        main_layout.addWidget(self.process_btn)
        
        # Results section with tabs
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Text Results
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.tabs.addTab(self.results_text, "Results")
        
        # Tab 2: Visualization
        self.visualization_widget = QWidget()
        self.visualization_layout = QVBoxLayout(self.visualization_widget)
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.visualization_layout.addWidget(self.canvas)
        self.tabs.addTab(self.visualization_widget, "Visualization")
        
        # Tab 3: Intermediate Images
        self.intermediate_widget = QWidget()
        self.intermediate_layout = QVBoxLayout(self.intermediate_widget)
        self.intermediate_figure = Figure(figsize=(10, 8))
        self.intermediate_canvas = FigureCanvas(self.intermediate_figure)
        self.intermediate_layout.addWidget(self.intermediate_canvas)
        self.tabs.addTab(self.intermediate_widget, "Intermediate Images")
        
        results_layout.addWidget(self.tabs)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
    def upload_fingerprint(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Fingerprint Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            self.fingerprint_path = file_path
            pixmap = QPixmap(file_path)
            self.fingerprint_label.setPixmap(
                pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            
    def upload_blood_sample(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Blood Sample Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            self.blood_sample_path = file_path
            pixmap = QPixmap(file_path)
            self.blood_label.setPixmap(
                pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
    
    def analyze_blood_group(self):
        if not self.fingerprint_path:
            QMessageBox.warning(self, "Warning", "Please upload a fingerprint image first.")
            return
            
        if not self.blood_sample_path:
            QMessageBox.warning(self, "Warning", "Please upload a blood sample image first.")
            return
            
        # Disable button during analysis
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create and start analysis thread
        self.analysis_thread = AnalysisThread(self.fingerprint_path, self.blood_sample_path)
        self.analysis_thread.progress.connect(self.update_progress)
        self.analysis_thread.result.connect(self.analysis_complete)
        self.analysis_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def analysis_complete(self, results):
        # Re-enable button
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if 'error' in results:
            QMessageBox.critical(self, "Error", f"An error occurred during processing: {results['error']}")
            return
            
        # Display results
        fingerprint_result = results['fingerprint']
        blood_group = results['blood_group']
        confidence = results['confidence']
        analysis_data = results['analysis_data']
        
        result_message = f"""
        ANALYSIS RESULTS:
        ----------------------------
        Fingerprint Verification: {fingerprint_result}
        Blood Group: {blood_group}
        Confidence: {confidence * 100:.2f}%
        ----------------------------
        
        Method-specific Results:
        """
        
        for method, result, conf in zip(analysis_data['methods'], 
                                       analysis_data['results'], 
                                       analysis_data['confidences']):
            result_message += f"{method}: {result} ({(conf * 100):.1f}%)\n"
        
        result_message += """
        ----------------------------
        
        Note: This is a demonstration system. In a real clinical setting, 
        blood typing should be performed by trained professionals 
        using proper laboratory equipment and validation procedures.
        """
        
        self.results_text.setText(result_message)
        
        # Update visualization
        self.update_visualization(analysis_data)
        
        # Update intermediate images
        self.update_intermediate_images(analysis_data)
    
    def update_visualization(self, analysis_data):
        self.figure.clear()
        
        # Create bar chart of method confidences
        ax = self.figure.add_subplot(121)
        methods = analysis_data['methods']
        confidences = [c * 100 for c in analysis_data['confidences']]
        
        bars = ax.bar(methods, confidences, color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'])
        ax.set_ylabel('Confidence (%)')
        ax.set_title('Analysis Method Confidence')
        ax.set_ylim(0, 100)
        
        # Add value labels on bars
        for bar, confidence in zip(bars, confidences):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{confidence:.1f}%', ha='center', va='bottom')
        
        # Create pie chart of final result confidence
        ax2 = self.figure.add_subplot(122)
        confidence = analysis_data['final_confidence'] * 100
        sizes = [confidence, 100 - confidence]
        colors = ['#ff9999', '#dddddd']
        explode = (0.1, 0)  # explode the result slice
        
        ax2.pie(sizes, explode=explode, labels=['Confidence', 'Uncertainty'], 
                colors=colors, autopct='%1.1f%%', shadow=True, startangle=90)
        ax2.axis('equal')
        ax2.set_title(f'Final Result: {analysis_data["final_result"]}')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def update_intermediate_images(self, analysis_data):
        self.intermediate_figure.clear()
        intermediate_images = analysis_data['intermediate_images']
        
        # Create a grid of subplots for intermediate images
        rows = 2
        cols = 2
        
        # Agglutination images
        if 'agglutination' in intermediate_images:
            ax = self.intermediate_figure.add_subplot(rows, cols, 1)
            ax.imshow(intermediate_images['agglutination']['cleaned'], cmap='gray')
            ax.set_title('Agglutination Analysis')
            ax.axis('off')
        
        # Distribution images
        if 'distribution' in intermediate_images:
            ax = self.intermediate_figure.add_subplot(rows, cols, 2)
            ax.imshow(intermediate_images['distribution']['edges'], cmap='gray')
            ax.set_title('Cell Distribution Analysis')
            ax.axis('off')
        
        # Color images
        if 'color' in intermediate_images:
            ax = self.intermediate_figure.add_subplot(rows, cols, 3)
            ax.imshow(intermediate_images['color']['hue'], cmap='hsv')
            ax.set_title('Color Analysis (Hue)')
            ax.axis('off')
        
        # Texture images
        if 'texture' in intermediate_images:
            ax = self.intermediate_figure.add_subplot(rows, cols, 4)
            ax.imshow(intermediate_images['texture']['lbp'], cmap='gray')
            ax.set_title('Texture Analysis (LBP)')
            ax.axis('off')
        
        self.intermediate_figure.tight_layout()
        self.intermediate_canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application-wide font to avoid warnings
    font = QFont("Arial", 11)
    app.setFont(font)
    
    window = BloodGroupApp()
    window.show()
    sys.exit(app.exec_())
