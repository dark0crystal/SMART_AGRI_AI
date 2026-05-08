"""
Django TestCase classes for SMART AGRI AI model testing.
Integration with Django's testing framework.
"""

from django.test import TestCase
from pathlib import Path
import logging

from api.ai_service import predict_image_from_path, predict_text
from tests.test_config import VISION_TEST_CASES, TEXT_TEST_CASES
from tests.test_descriptions import get_all_text_test_inputs
from tests.test_data_generator import create_test_images

logger = logging.getLogger(__name__)


class VisionModelTestCase(TestCase):
    """Tests for vision (image) model."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        # Create test images
        cls.images_dir = Path(__file__).parent / "test_data" / "vision_images"
        cls.test_images = create_test_images(cls.images_dir)

    def test_healthy_lemon_image(self):
        """TC-1: Healthy lemon micro shoot classification."""
        test_case = next(
            (tc for tc in VISION_TEST_CASES if tc["id"] == "TC-1"), None
        )
        self.assertIsNotNone(test_case)

        if "TC-1" in self.test_images:
            image_path = self.test_images["TC-1"]
            result = predict_image_from_path(image_path)
            self.assertIsNotNone(result)
            self.assertEqual(
                result.get("predicted_label"),
                test_case["expected_class"],
                f"Expected {test_case['expected_class']}, "
                f"got {result.get('predicted_label')}",
            )

    def test_witch_broom_image(self):
        """TC-2: Witch broom lemon tree classification."""
        test_case = next(
            (tc for tc in VISION_TEST_CASES if tc["id"] == "TC-2"), None
        )
        self.assertIsNotNone(test_case)

        if "TC-2" in self.test_images:
            image_path = self.test_images["TC-2"]
            result = predict_image_from_path(image_path)
            self.assertIsNotNone(result)
            self.assertEqual(
                result.get("predicted_label"),
                test_case["expected_class"],
                f"Expected {test_case['expected_class']}, "
                f"got {result.get('predicted_label')}",
            )

    def test_non_lemon_image(self):
        """TC-3: Non-lemon image (mango trees) should be Unknown."""
        test_case = next(
            (tc for tc in VISION_TEST_CASES if tc["id"] == "TC-3"), None
        )
        self.assertIsNotNone(test_case)

        if "TC-3" in self.test_images:
            image_path = self.test_images["TC-3"]
            result = predict_image_from_path(image_path)
            self.assertIsNotNone(result)
            self.assertEqual(
                result.get("predicted_label"),
                test_case["expected_class"],
                f"Expected {test_case['expected_class']}, "
                f"got {result.get('predicted_label')}",
            )

    def test_sky_image(self):
        """TC-6: Sky without trees should be Unknown."""
        test_case = next(
            (tc for tc in VISION_TEST_CASES if tc["id"] == "TC-6"), None
        )
        self.assertIsNotNone(test_case)

        if "TC-6" in self.test_images:
            image_path = self.test_images["TC-6"]
            result = predict_image_from_path(image_path)
            self.assertIsNotNone(result)
            self.assertEqual(
                result.get("predicted_label"),
                test_case["expected_class"],
                f"Expected {test_case['expected_class']}, "
                f"got {result.get('predicted_label')}",
            )

    def test_blurred_image(self):
        """TC-8: Blurred image should be Unknown."""
        test_case = next(
            (tc for tc in VISION_TEST_CASES if tc["id"] == "TC-8"), None
        )
        self.assertIsNotNone(test_case)

        if "TC-8" in self.test_images:
            image_path = self.test_images["TC-8"]
            result = predict_image_from_path(image_path)
            self.assertIsNotNone(result)
            self.assertEqual(
                result.get("predicted_label"),
                test_case["expected_class"],
                f"Expected {test_case['expected_class']}, "
                f"got {result.get('predicted_label')}",
            )


class TextModelTestCase(TestCase):
    """Tests for text (description) model."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        cls.text_inputs = get_all_text_test_inputs()

    def test_healthy_description_artificial(self):
        """TC-11: Artificial healthy lemon description."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-11"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-11")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )

    def test_witch_broom_description_artificial(self):
        """TC-12: Artificial witch broom description."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-12"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-12")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )

    def test_disease_description_artificial(self):
        """TC-13: Artificial disease description (non-witch-broom)."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-13"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-13")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )

    def test_healthy_description_available(self):
        """TC-14: Available healthy description."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-14"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-14")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )

    def test_witch_broom_description_available(self):
        """TC-15: Available witch broom description."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-15"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-15")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )

    def test_disease_description_available(self):
        """TC-16: Available unhealthy description."""
        test_case = next(
            (tc for tc in TEXT_TEST_CASES if tc["id"] == "TC-16"), None
        )
        self.assertIsNotNone(test_case)

        text = self.text_inputs.get("TC-16")
        self.assertIsNotNone(text)
        result = predict_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(
            result.get("predicted_label"),
            test_case["expected_class"],
            f"Expected {test_case['expected_class']}, "
            f"got {result.get('predicted_label')}",
        )
