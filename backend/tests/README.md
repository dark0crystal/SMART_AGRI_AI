# SMART AGRI AI - Unit Testing Framework

## Overview

This testing framework implements comprehensive unit testing for the SMART AGRI AI models as specified in Section 5.3.1 of the project documentation. It tests both the **vision model** (image processing) and **text model** (text recognition) to ensure they correctly classify lemon diseases.

## Classification Classes

The models classify inputs into three categories:

| Class | Description |
|-------|-------------|
| **Healthy** | Lemon image/description with healthy overall features or characteristics |
| **Witch Broom** | Lemon image/description with witch broom disease symptoms |
| **Unknown** | Images/descriptions with: other diseases (not Witch Broom), non-lemon plants, unclear/blurred content, or no plant content |

## Data Types Used in Testing

| Data Type | Source | Purpose |
|-----------|--------|---------|
| **Artificial** | AI-generated data | Test performance against common standards |
| **Available** | Public datasets | Test robustness of the model |
| **Real** | Personally taken/written | Test real-world performance |

## Test Cases

### Vision Model Test Cases (TC-1 to TC-10)

| TC ID | Data Type | Input Description | Expected Class | Status |
|-------|-----------|-------------------|-----------------|--------|
| TC-1 | Artificial | Micro shoot of healthy lemon tree branch | Healthy | - |
| TC-2 | Artificial | Big lemon tree with witch broom symptoms | Witch Broom | - |
| TC-3 | Artificial | Bunch of mango trees | Unknown | - |
| TC-4 | Available | Healthy lemon tree from public dataset | Healthy | - |
| TC-5 | Available | Lemon tree with witch broom from dataset | Witch Broom | - |
| TC-6 | Available | Cloudy sky without trees | Unknown | - |
| TC-7 | Available | Lemon branches with rot foot disease | Unknown | - |
| TC-8 | Available | Blurred micro shot of healthy branches | Unknown | - |
| TC-9 | Real | Whole healthy lemon tree (real photo) | Healthy | - |
| TC-10 | Real | Lemon tree with witch broom (Dr. AL-Sadi) | Witch Broom | - |

### Text Model Test Cases (TC-11 to TC-19)

| TC ID | Data Type | Input Description | Expected Class | Status |
|-------|-----------|-------------------|-----------------|--------|
| TC-11 | Artificial | Artificial healthy lemon description | Healthy | - |
| TC-12 | Artificial | Artificial witch broom description | Witch Broom | - |
| TC-13 | Artificial | Lemon with greening disease | Unknown | - |
| TC-14 | Available | Website description of healthy lemon leaves | Healthy | - |
| TC-15 | Available | Website description of witch broom symptoms | Witch Broom | - |
| TC-16 | Available | Website description of unhealthy leaves | Unknown | - |
| TC-17 | Real | Real description of healthy lemon tree | Healthy | - |
| TC-18 | Real | Real description of witch broom disease | Witch Broom | - |
| TC-19 | Real | Real description with unclear symptoms | Unknown | - |

## Project Structure

```
backend/tests/
├── __init__.py                 # Package initialization
├── test_config.py              # Test case definitions
├── test_data_generator.py       # Artificial test image generation
├── test_descriptions.py         # Test text descriptions
├── test_results.py              # Result management & reporting
├── test_runner.py               # Main test orchestration
├── django_test_cases.py         # Django TestCase integration
├── README.md                    # This file
├── test_data/
│   ├── vision_images/           # Vision model test images
│   │   ├── TC-1_healthy_micro_shoot.png
│   │   ├── TC-2_witch_broom_tree.png
│   │   ├── TC-3_mango_trees.png
│   │   ├── TC-6_cloudy_sky.png
│   │   └── TC-8_blurred_lemon.png
│   └── text_descriptions/       # Text model test data
└── test_results/                # Generated test reports
    ├── vision_test_results_*.csv
    ├── vision_test_results_*.json
    ├── vision_test_results_*.html
    ├── text_test_results_*.csv
    ├── text_test_results_*.json
    └── text_test_results_*.html
```

## Running the Tests

### Option 1: Using the Standalone Test Runner

Run the comprehensive test suite that executes all test cases and generates reports:

```bash
cd backend
python tests/test_runner.py
```

This will:
1. Create artificial test images
2. Run all vision model tests (TC-1 to TC-10)
3. Run all text model tests (TC-11 to TC-19)
4. Generate reports in CSV, JSON, and HTML formats
5. Display summary statistics

### Option 2: Using Django's Test Framework

Run tests using Django's built-in testing framework:

```bash
cd backend
python manage.py test tests.django_test_cases.VisionModelTestCase
python manage.py test tests.django_test_cases.TextModelTestCase
```

Or run all tests at once:

```bash
python manage.py test tests.django_test_cases
```

### Option 3: Running Individual Tests

To run specific test cases:

```bash
# Run a specific vision test
python manage.py test tests.django_test_cases.VisionModelTestCase.test_healthy_lemon_image

# Run a specific text test
python manage.py test tests.django_test_cases.TextModelTestCase.test_witch_broom_description_artificial
```

## Test Reports

After running tests, the following reports are generated in `backend/tests/test_results/`:

### CSV Report
Human-readable tabular format suitable for spreadsheets and documentation:
```
Test Case ID,Data Type,Input Description,Expected Class,Actual Class,Confidence,Status,Error
TC-1,Artificial,Artificial image of a micro shoot...,Healthy,Healthy,95.2%,Pass,
TC-2,Artificial,Artificial image of a big lemon tree...,Witch Broom,Witch Broom,92.1%,Pass,
...
```

### JSON Report
Structured format with detailed metadata:
```json
{
  "summary": {
    "model_type": "vision",
    "total_tests": 10,
    "passed": 8,
    "failed": 2,
    "errors": 0,
    "pass_rate": "80.0%",
    "start_time": "2024-05-08T10:30:15",
    "end_time": "2024-05-08T10:35:42",
    "duration_seconds": 327
  },
  "results": [
    {
      "test_case_id": "TC-1",
      "data_type": "Artificial",
      "input_description": "Artificial image of a micro shoot...",
      "expected_class": "Healthy",
      "actual_class": "Healthy",
      "confidence": "95.20%",
      "status": "Pass",
      "error_message": "",
      "timestamp": "2024-05-08T10:30:45"
    },
    ...
  ]
}
```

### HTML Report
Interactive visual report with color-coded results:
- Green for PASS
- Red for FAIL
- Orange for ERROR

Open the HTML file in a browser for interactive viewing.

## Interpreting Results

### Test Status Legend

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| **Pass** | Actual class matches expected class | None - test successful |
| **Fail** | Actual class differs from expected | Review model predictions and fine-tune if needed |
| **Error** | Test execution failed (exception) | Check error message and fix infrastructure issue |

### Pass Rate Analysis

```
Pass Rate = (Passed Tests / Total Tests) × 100%
```

- **90-100%**: Excellent model performance
- **80-90%**: Good performance, minor improvements needed
- **70-80%**: Acceptable, but improvements recommended
- **<70%**: Significant issues requiring model retraining or adjustment

### Example Interpretation

If TC-1 shows:
```
Expected: Healthy
Actual: Witch Broom
Confidence: 68.5%
Status: Fail
```

This indicates the model misclassified a healthy lemon image as witch broom with 68.5% confidence. This could suggest:
1. The model needs retraining with more healthy examples
2. Image preprocessing might be affecting results
3. The test image might not be representative

## Adding Custom Test Cases

To add new test cases:

### 1. Add to Test Configuration

Edit `test_config.py`:

```python
NEW_TEST_CASE = {
    "id": "TC-20",
    "data_type": "Real",  # or "Artificial"/"Available"
    "input_description": "Description of your test case",
    "expected_class": "Healthy",  # or "Witch Broom"/"Unknown"
    "category": "vision",  # or "text"
}

VISION_TEST_CASES.append(NEW_TEST_CASE)  # For vision
# or
TEXT_TEST_CASES.append(NEW_TEST_CASE)  # For text
```

### 2. Add Test Data

For vision tests:
- Create or place the test image in `test_data/vision_images/`
- Follow naming: `TC-20_description.png`

For text tests:
- Add to `test_descriptions.py`:

```python
NEW_TEXT_DESCRIPTION = {
    "TC-20": {
        "text": "Your detailed description here...",
        "expected_class": "Healthy",
        "data_type": "Real",
    },
}
ALL_TEXT_DESCRIPTIONS.update(NEW_TEXT_DESCRIPTION)
```

## Dependencies

The testing framework requires:

```
Django>=6.0.3
Pillow>=10.0.0
torch>=2.5.0
torchvision>=0.20.0
timm>=1.0.0
scikit-learn>=1.5.0
```

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Troubleshooting

### Issue: "VisionDependenciesMissing" Error

**Solution**: Install vision dependencies
```bash
pip install torch torchvision timm
```

### Issue: "Text model folder not found"

**Solution**: Ensure text class files exist in `models/text_classes/`

### Issue: "Vision model file not found"

**Solution**: Set correct path in Django settings:
```python
VISION_MODEL_PATH = "/path/to/models/final_model.pth"
TEXT_MODEL_PATH = "/path/to/models/text_classes"
```

### Issue: No test images generated

**Solution**: Manually create test images by running:
```bash
python tests/test_data_generator.py
```

## Performance Metrics

After running tests, analyze performance by data type:

### By Data Type
```
Artificial Data:  70% pass rate (3/4 tests passed)
Available Data:   85% pass rate (5/6 tests passed)
Real Data:        50% pass rate (1/2 tests passed)
```

### By Classification Class
```
Healthy:      90% accuracy (9/10 tests)
Witch Broom:  80% accuracy (8/10 tests)
Unknown:      75% accuracy (6/8 tests)
```

## Documentation References

This testing framework implements requirements from:
- **Section 5.3.1**: Unit Testing methodology
- **Table 5.3**: Data types used in testing
- **Table 5.4**: Image processing model test cases
- **Table 5.5**: Text recognition model test cases

## Support and Maintenance

### Regular Testing Schedule

- **Development**: After each model update
- **Testing Phase**: Daily during active debugging
- **Production**: Weekly validation
- **Release**: Final certification before deployment

### Updating Test Cases

When model performance changes significantly:
1. Review failed test cases
2. Determine if failure is due to model improvement or regression
3. Update expected classes if intentional model changes were made
4. Document rationale in commit messages

## Example Test Execution Output

```
================================================================================
SMART AGRI AI - Comprehensive Unit Test Suite
================================================================================

================================================================================
Starting Vision Model Tests
================================================================================

Running TC-1: Artificial image of a micro shoot for a healthy lemon tree branch.
  Using image: /path/to/TC-1_healthy_micro_shoot.png
  ✓ PASS - Predicted: Healthy

Running TC-2: Artificial image of a big lemon tree with witch broom disease symptoms.
  Using image: /path/to/TC-2_witch_broom_tree.png
  ✓ PASS - Predicted: Witch Broom

...

================================================================================
Vision Model Tests Complete
================================================================================

================================================================================
Starting Text Model Tests
================================================================================

Running TC-11: Artificially created description for a healthy lemon plant.
  Input text: The lemon tree looks very healthy with vibrant green leaves...
  ✓ PASS - Predicted: Healthy

...

================================================================================
TEST EXECUTION SUMMARY
================================================================================

Vision Model Tests:
  Total Tests: 10
  Passed: 8
  Failed: 2
  Errors: 0
  Pass Rate: 80.0%

Text Model Tests:
  Total Tests: 9
  Passed: 7
  Failed: 2
  Errors: 0
  Pass Rate: 77.8%

Results saved to: /path/to/tests/test_results

================================================================================

✓ All tests completed successfully!
```

## See Also

- [Backend README](../README.md)
- [Project Documentation](../../Chapter5_Implementation.html)
- [AI Service Module](../api/ai_service.py)
