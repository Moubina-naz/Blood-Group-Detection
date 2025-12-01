import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QTextEdit, QMessageBox, QProgressBar)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import skimage.io as ski
import skimage.filters as skif
import skimage.color as skic
import skimage.morphology as skim
import skimage.feature as skifeat
import skimage.segmentation as skiseg
import skimage.exposure as skiexp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
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
#mammia
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
        ridges = cv2.ximgproc.thinning(binary)
        
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
        
        # Method 1: Agglutination pattern analysis
        agglutination_result, agglutination_confidence = self.analyze_agglutination_patterns(img_processed)
        results.append(agglutination_result)
        confidence_scores.append(agglutination_confidence)
        
        # Method 2: Cell distribution analysis
        distribution_result, distribution_confidence = self.analyze_cell_distribution(img_processed)
        results.append(distribution_result)
        confidence_scores.append(distribution_confidence)
        
        # Method 3: Color-based analysis
        color_result, color_confidence = self.analyze_blood_color(img)
        results.append(color_result)
        confidence_scores.append(color_confidence)
        
        # Combine results
        final_result, final_confidence = self.combine_analyses(results, confidence_scores)
        
        # Prepare analysis data for display
        analysis_data = {
            'methods': ['Agglutination', 'Distribution', 'Color'],
            'results': results,
            'confidences': confidence_scores,
            'final_result': final_result,
            'final_confidence': final_confidence
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
        regions = skim.regionprops(labeled)
        
        # Calculate features
        num_regions = len(regions)
        if num_regions == 0:
            return "Inconclusive", 0.0
            
        areas = [r.area for r in regions]
        avg_area = np.mean(areas)
        area_std = np.std(areas)
        
        # Agglutination detection logic
        if num_regions < 10 and avg_area > 100:
            # Few large clumps suggest agglutination (positive reaction)
            blood_group = "A+"
            confidence = min(0.95, 0.7 + (avg_area / 1000))
        elif num_regions > 50 and avg_area < 30:
            # Many small cells suggest no agglutination (negative reaction)
            blood_group = "O+"
            confidence = min(0.95, 0.7 + (50 / num_regions))
        else:
            # Intermediate case
            blood_group = "B+"
            confidence = 0.6
            
        return blood_group, confidence
    
    def analyze_cell_distribution(self, img):
        # Edge detection to find cell boundaries
        edges = skifeat.canny(img, sigma=1.0)
        
        # Distance transform to find cell centers
        distance = skif.sobel(img)
        
        # Find local maxima as cell centers
        coordinates = skifeat.peak_local_max(
            distance, 
            min_distance=7, 
            threshold_abs=0.1,
            indices=True
        )
        
        num_cells = len(coordinates)
        
        # Analyze distribution pattern
        if num_cells < 20:
            blood_group = "AB+"
            confidence = 0.75
        elif num_cells > 100:
            blood_group = "O-"
            confidence = 0.8
        else:
            blood_group = "A-"
            confidence = 0.65
            
        return blood_group, confidence
    
    def analyze_blood_color(self, img):
        if len(img.shape) != 3:
            return "Inconclusive", 0.0
            
        # Convert to HSV color space
        img_hsv = skic.rgb2hsv(img)
        
        # Extract hue and saturation
        hue = img_hsv[:, :, 0]
        saturation = img_hsv[:, :, 1]
        
        # Calculate average hue and saturation
        avg_hue = np.mean(hue)
        avg_saturation = np.mean(saturation)
        
        # Determine blood group based on color characteristics
        if avg_saturation > 0.5:
            if avg_hue < 0.05 or avg_hue > 0.9:  # Red tones
                blood_group = "A+"
                confidence = 0.8
            else:
                blood_group = "B+"
                confidence = 0.7
        else:
            if avg_hue < 0.1:  # Very red
                blood_group = "O+"
                confidence = 0.75
            else:
                blood_group = "AB+"
                confidence = 0.65
                
        return blood_group, confidence
    
    def combine_analyses(self, results, confidences):
        # Weighted voting system
        blood_groups = {}
        for result, confidence in zip(results, confidences):
            if result in blood_groups:
                blood_groups[result] += confidence
            else:
                blood_groups[result] = confidence
        
        # Find the result with highest confidence
        best_result = max(blood_groups, key=blood_groups.get)
        total_confidence = blood_groups[best_result] / len(confidences)
        
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
        self.setGeometry(100, 100, 1000, 800)
        
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
        
        # Results section
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        # Analysis visualization
        visualization_group = QGroupBox("Analysis Visualization")
        visualization_layout = QVBoxLayout()
        self.figure = Figure(figsize=(10, 4))
        self.canvas = FigureCanvas(self.figure)
        visualization_layout.addWidget(self.canvas)
        visualization_group.setLayout(visualization_layout)
        main_layout.addWidget(visualization_group)
        
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
    
    def update_visualization(self, analysis_data):
        self.figure.clear()
        
        # Create bar chart of method confidences
        ax = self.figure.add_subplot(121)
        methods = analysis_data['methods']
        confidences = [c * 100 for c in analysis_data['confidences']]
        
        bars = ax.bar(methods, confidences, color=['#ff9999', '#66b3ff', '#99ff99'])
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application-wide font to avoid warnings
    font = QFont("Arial", 11)
    app.setFont(font)
    
    window = BloodGroupApp()
    window.show()
    sys.exit(app.exec_())
