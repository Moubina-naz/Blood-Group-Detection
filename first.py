import sys
import skimage.io as ski
import skimage.filters as skif
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QTextEdit, QMessageBox)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

class BloodGroupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.fingerprint_path = None
        self.blood_sample_path = None
        
    def initUI(self):
        self.setWindowTitle('Blood Group Identification System')
        self.setGeometry(100, 100, 900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title = QLabel('Blood Group Identification System')
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
        
        # Process button
        process_btn = QPushButton('Analyze Blood Group')
        process_btn.clicked.connect(self.analyze_blood_group)
        process_btn.setStyleSheet("font-size: 16px; padding: 10px;")
        main_layout.addWidget(process_btn)
        
        # Results section
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
    def upload_fingerprint(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Fingerprint Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
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
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
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
            
        try:
            # Process fingerprint (placeholder for actual fingerprint processing)
            fingerprint_result = self.process_fingerprint(self.fingerprint_path)
            
            # Process blood sample
            blood_group = self.process_blood_sample(self.blood_sample_path)
            
            # Display results
            result_message = f"""
            ANALYSIS RESULTS:
            ----------------------------
            Fingerprint Verification: {fingerprint_result}
            Blood Group: {blood_group}
            ----------------------------
            
            Note: This is a demonstration. In a real clinical setting, 
            blood typing should be performed by trained professionals 
            using proper laboratory equipment.
            """
            
            self.results_text.setText(result_message)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during processing: {str(e)}")
    
    def process_fingerprint(self, image_path):
        # Placeholder for actual fingerprint processing
        # In a real application, this would verify the fingerprint
        return "Verified (Demo)"
    
    def process_blood_sample(self, image_path):
        try:
            # Read the image
            img = ski.imread(image_path)
            
            # Convert to grayscale if it's a color image
            if len(img.shape) == 3:
                # Extract green channel (as in your original code)
                green_channel = img[:, :, 1]
            else:
                green_channel = img
                
            # Apply Otsu's threshold
            threshold = skif.threshold_otsu(green_channel, nbins=256)
            binary_image = green_channel > threshold
            
            # Analyze the binary image to detect blood group patterns
            # This is a simplified approach - real blood typing would be more complex
            blood_group = self.detect_blood_group(binary_image)
            
            return blood_group
            
        except Exception as e:
            raise Exception(f"Blood sample processing error: {str(e)}")
    
    def detect_blood_group(self, binary_image):
        # This is a simplified simulation of blood group detection
        # In a real application, this would involve more sophisticated
        # image processing and pattern recognition
        
        # Calculate some image properties that might correlate with blood group patterns
        white_pixels = np.sum(binary_image)
        total_pixels = binary_image.size
        white_ratio = white_pixels / total_pixels
        
        # Simulate different blood groups based on image characteristics
        # This is just a demonstration - not medically accurate
        if white_ratio < 0.2:
            return "O+"
        elif white_ratio < 0.4:
            return "A+"
        elif white_ratio < 0.6:
            return "B+"
        elif white_ratio < 0.8:
            return "AB+"
        else:
            return "O-"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BloodGroupApp()
    window.show()
    sys.exit(app.exec_())
