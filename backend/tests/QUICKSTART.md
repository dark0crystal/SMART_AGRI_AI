"""
Quick Start Guide for SMART AGRI AI Testing Framework

This file contains quick examples of running tests.
"""

# ============================================================================
# QUICK START
# ============================================================================

# 1. SETUP
# --------
# Ensure all dependencies are installed:
# cd backend
# pip install -r requirements.txt

# 2. RUN ALL TESTS
# ----------------
# Option A: Using Django Management Command
cd backend
python manage.py run_ai_tests

# Option B: Using the Test Runner Directly
python tests/test_runner.py

# 3. RUN SPECIFIC TEST SUITES
# ----------------------------
# Vision tests only
python manage.py run_ai_tests --vision-only

# Text tests only
python manage.py run_ai_tests --text-only

# Both vision and text (explicitly)
python manage.py run_ai_tests --vision --text

# 4. GENERATE TEST IMAGES ONLY
# ----------------------------
# Create artificial test images without running tests
python manage.py run_ai_tests --generate-images-only

# 5. ANALYZE EXISTING REPORTS
# ---------------------------
# Analyze a test report
python manage.py run_ai_tests --analyze tests/test_results/vision_test_results_20240508_103015.json

# View latest vision test results
python -c "from tests.test_utils import TestResultAnalyzer; from pathlib import Path; \
reports = sorted(Path('tests/test_results').glob('vision_test_results_*.json'), reverse=True); \
analyzer = TestResultAnalyzer(reports[0]) if reports else None; \
analyzer.print_summary() if analyzer else print('No reports found')"

# 6. COMPARE TEST REPORTS
# -----------------------
# Compare two test runs to see improvement
python manage.py run_ai_tests --compare \
    tests/test_results/vision_test_results_20240508_103015.json \
    tests/test_results/vision_test_results_20240508_110530.json

# 7. RUN WITH CUSTOM OUTPUT DIRECTORY
# ------------------------------------
# Save results to custom location
python manage.py run_ai_tests --output-dir my_test_results

# 8. USING DJANGO'S TEST FRAMEWORK
# --------------------------------
# Run Django tests
python manage.py test tests.django_test_cases

# Run specific test class
python manage.py test tests.django_test_cases.VisionModelTestCase

# Run specific test method
python manage.py test tests.django_test_cases.VisionModelTestCase.test_healthy_lemon_image

# Run with verbose output
python manage.py test tests.django_test_cases -v 2

# ============================================================================
# EXAMINING RESULTS
# ============================================================================

# View HTML report in browser
start tests/test_results/vision_test_results_20240508_103015.html  # Windows
open tests/test_results/vision_test_results_20240508_103015.html   # macOS
xdg-open tests/test_results/vision_test_results_20240508_103015.html  # Linux

# View CSV results in spreadsheet
# Open with Excel, Google Sheets, or LibreOffice:
# tests/test_results/vision_test_results_20240508_103015.csv

# View JSON results
cat tests/test_results/vision_test_results_20240508_103015.json

# ============================================================================
# FILE STRUCTURE AFTER FIRST RUN
# ============================================================================
backend/tests/
├── test_data/
│   └── vision_images/  # Generated test images
│       ├── TC-1_healthy_micro_shoot.png
│       ├── TC-2_witch_broom_tree.png
│       ├── TC-3_mango_trees.png
│       ├── TC-6_cloudy_sky.png
│       └── TC-8_blurred_lemon.png
│
└── test_results/  # Test reports (created after first run)
    ├── vision_test_results_20240508_103015.csv
    ├── vision_test_results_20240508_103015.json
    ├── vision_test_results_20240508_103015.html
    ├── text_test_results_20240508_103015.csv
    ├── text_test_results_20240508_103015.json
    └── text_test_results_20240508_103015.html

# ============================================================================
# TYPICAL TESTING WORKFLOW
# ============================================================================

# 1. Initial setup
cd backend
pip install -r requirements.txt

# 2. Generate test images
python manage.py run_ai_tests --generate-images-only

# 3. Run all tests
python manage.py run_ai_tests

# 4. Review results
# Open HTML report for visual review:
start tests/test_results/vision_test_results_*.html

# 5. Analyze results in detail
python manage.py run_ai_tests --analyze tests/test_results/vision_test_results_*.json

# 6. After model improvements, run again
python manage.py run_ai_tests

# 7. Compare with previous results
python manage.py run_ai_tests --compare \
    tests/test_results/vision_test_results_old.json \
    tests/test_results/vision_test_results_new.json

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If vision model is not found:
# - Check VISION_MODEL_PATH in config/settings.py
# - Ensure final_model.pth or best_model.pth exists in models/ folder

# If text model is not found:
# - Check TEXT_MODEL_PATH in config/settings.py
# - Ensure text_classes folder exists with *.txt files

# If tests fail with missing dependencies:
pip install torch torchvision timm scikit-learn pillow

# If Django errors occur:
python manage.py check

# ============================================================================
# INTERPRETING TEST RESULTS
# ============================================================================

# PASS:  Expected class == Predicted class → Model prediction was correct
# FAIL:  Expected class != Predicted class → Model made wrong prediction
# ERROR: Test could not be executed → Infrastructure issue

# Example analysis:
# Vision Pass Rate: 80% (8/10)
# - Artificial: 2/2 (100%)
# - Available: 5/6 (83%)
# - Real: 1/2 (50%)  ← Needs investigation

# Recommendation: Improve real-world performance with more real training data

# ============================================================================
