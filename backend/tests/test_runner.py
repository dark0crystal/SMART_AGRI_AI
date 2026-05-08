"""
Main test runner for SMART AGRI AI models.
Executes all test cases and generates comprehensive reports.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from PIL import Image
import torch

from api.ai_service import predict_image_from_path, predict_text
from tests.test_config import VISION_TEST_CASES, TEXT_TEST_CASES
from tests.test_descriptions import get_test_description, get_all_text_test_inputs
from tests.test_data_generator import create_test_images
from tests.test_results import TestResult, TestSuite

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class AIModelTestRunner:
    """Orchestrates testing of AI models."""

    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or (Path(__file__).parent / "test_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.vision_suite = TestSuite("vision")
        self.text_suite = TestSuite("text")

    def run_vision_tests(self) -> TestSuite:
        """Run all vision model tests."""
        logger.info("=" * 80)
        logger.info("Starting Vision Model Tests")
        logger.info("=" * 80)

        # Create test images
        images_dir = Path(__file__).parent / "test_data" / "vision_images"
        logger.info(f"Creating test images in {images_dir}")
        test_images = create_test_images(images_dir)

        for test_case in VISION_TEST_CASES:
            test_id = test_case["id"]
            logger.info(f"\nRunning {test_id}: {test_case['input_description']}")

            result = TestResult(
                test_case_id=test_id,
                data_type=test_case["data_type"],
                input_description=test_case["input_description"],
                expected_class=test_case["expected_class"],
            )

            # Check if we have a test image
            if test_id in test_images:
                try:
                    image_path = test_images[test_id]
                    logger.info(f"  Using image: {image_path}")

                    # Run prediction
                    prediction_result = predict_image_from_path(image_path)

                    if prediction_result:
                        result.actual_class = prediction_result.get("predicted_label")
                        result.confidence = prediction_result.get("confidence")

                        # Determine status
                        if result.actual_class == result.expected_class:
                            result.status = "Pass"
                            logger.info(f"  ✓ PASS - Predicted: {result.actual_class}")
                        else:
                            result.status = "Fail"
                            logger.warning(
                                f"  ✗ FAIL - Expected: {result.expected_class}, "
                                f"Got: {result.actual_class}"
                            )
                    else:
                        result.status = "Error"
                        result.error_message = "Prediction returned None"
                        logger.error(f"  ✗ ERROR - Prediction failed")

                except Exception as e:
                    result.status = "Error"
                    result.error_message = str(e)
                    logger.exception(f"  ✗ ERROR - {str(e)}")
            else:
                result.status = "Error"
                result.error_message = f"Test image not found"
                logger.warning(f"  ✗ ERROR - No test image available")

            self.vision_suite.add_result(result)

        logger.info("\n" + "=" * 80)
        logger.info("Vision Model Tests Complete")
        logger.info("=" * 80)
        self.vision_suite.finalize()

        return self.vision_suite

    def run_text_tests(self) -> TestSuite:
        """Run all text model tests."""
        logger.info("\n" + "=" * 80)
        logger.info("Starting Text Model Tests")
        logger.info("=" * 80)

        text_inputs = get_all_text_test_inputs()

        for test_case in TEXT_TEST_CASES:
            test_id = test_case["id"]
            logger.info(f"\nRunning {test_id}: {test_case['input_description']}")

            result = TestResult(
                test_case_id=test_id,
                data_type=test_case["data_type"],
                input_description=test_case["input_description"],
                expected_class=test_case["expected_class"],
            )

            if test_id in text_inputs:
                try:
                    text_input = text_inputs[test_id]
                    logger.info(f"  Input text: {text_input[:60]}...")

                    # Run prediction
                    prediction_result = predict_text(text_input)

                    if prediction_result:
                        result.actual_class = prediction_result.get("predicted_label")
                        result.confidence = prediction_result.get("confidence")

                        # Determine status
                        if result.actual_class == result.expected_class:
                            result.status = "Pass"
                            logger.info(f"  ✓ PASS - Predicted: {result.actual_class}")
                        else:
                            result.status = "Fail"
                            logger.warning(
                                f"  ✗ FAIL - Expected: {result.expected_class}, "
                                f"Got: {result.actual_class}"
                            )
                    else:
                        result.status = "Error"
                        result.error_message = "Prediction returned None"
                        logger.error(f"  ✗ ERROR - Prediction failed")

                except Exception as e:
                    result.status = "Error"
                    result.error_message = str(e)
                    logger.exception(f"  ✗ ERROR - {str(e)}")
            else:
                result.status = "Error"
                result.error_message = "Test description not found"
                logger.warning(f"  ✗ ERROR - No test description available")

            self.text_suite.add_result(result)

        logger.info("\n" + "=" * 80)
        logger.info("Text Model Tests Complete")
        logger.info("=" * 80)
        self.text_suite.finalize()

        return self.text_suite

    def run_all_tests(self) -> None:
        """Run all tests and generate reports."""
        logger.info("\n" + "=" * 80)
        logger.info("SMART AGRI AI - Comprehensive Unit Test Suite")
        logger.info("=" * 80 + "\n")

        # Run tests
        self.run_vision_tests()
        self.run_text_tests()

        # Generate reports
        self.generate_reports()

        # Print summary
        self.print_summary()

    def generate_reports(self) -> None:
        """Generate test reports in multiple formats."""
        logger.info("\nGenerating test reports...")

        timestamp = self.vision_suite.start_time.strftime("%Y%m%d_%H%M%S")

        # Vision reports
        vision_csv = self.results_dir / f"vision_test_results_{timestamp}.csv"
        vision_json = self.results_dir / f"vision_test_results_{timestamp}.json"
        vision_html = self.results_dir / f"vision_test_results_{timestamp}.html"

        self.vision_suite.save_csv(vision_csv)
        self.vision_suite.save_json(vision_json)
        self.vision_suite.save_html_report(vision_html)

        # Text reports
        text_csv = self.results_dir / f"text_test_results_{timestamp}.csv"
        text_json = self.results_dir / f"text_test_results_{timestamp}.json"
        text_html = self.results_dir / f"text_test_results_{timestamp}.html"

        self.text_suite.save_csv(text_csv)
        self.text_suite.save_json(text_json)
        self.text_suite.save_html_report(text_html)

        logger.info(f"Reports generated in {self.results_dir}")

    def print_summary(self) -> None:
        """Print test summary to console."""
        vision_summary = self.vision_suite.get_summary()
        text_summary = self.text_suite.get_summary()

        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)

        print("\nVision Model Tests:")
        print(f"  Total Tests: {vision_summary['total_tests']}")
        print(f"  Passed: {vision_summary['passed']}")
        print(f"  Failed: {vision_summary['failed']}")
        print(f"  Errors: {vision_summary['errors']}")
        print(f"  Pass Rate: {vision_summary['pass_rate']}")

        print("\nText Model Tests:")
        print(f"  Total Tests: {text_summary['total_tests']}")
        print(f"  Passed: {text_summary['passed']}")
        print(f"  Failed: {text_summary['failed']}")
        print(f"  Errors: {text_summary['errors']}")
        print(f"  Pass Rate: {text_summary['pass_rate']}")

        print(f"\nResults saved to: {self.results_dir}")
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    runner = AIModelTestRunner()

    try:
        runner.run_all_tests()
        print("\n✓ All tests completed successfully!")
    except Exception as e:
        logger.exception("Test execution failed")
        print(f"\n✗ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
