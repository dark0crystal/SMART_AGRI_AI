"""
Utility functions for test data management and analysis.
"""

import json
from pathlib import Path
from typing import dict, list
from datetime import datetime

from tests.test_config import ALL_TEST_CASES, DATA_TYPES, CLASSIFICATION_CLASSES


class TestDataManager:
    """Manages test data and analysis."""

    @staticmethod
    def get_tests_by_category(category: str) -> list[dict]:
        """Get test cases filtered by category (vision or text)."""
        return [tc for tc in ALL_TEST_CASES if tc.get("category") == category]

    @staticmethod
    def get_tests_by_data_type(data_type: str) -> list[dict]:
        """Get test cases filtered by data type."""
        return [tc for tc in ALL_TEST_CASES if tc.get("data_type") == data_type]

    @staticmethod
    def get_tests_by_expected_class(expected_class: str) -> list[dict]:
        """Get test cases filtered by expected classification."""
        return [tc for tc in ALL_TEST_CASES if tc.get("expected_class") == expected_class]

    @staticmethod
    def get_test_case(test_id: str) -> dict:
        """Get a specific test case by ID."""
        for tc in ALL_TEST_CASES:
            if tc.get("id") == test_id:
                return tc
        return None

    @staticmethod
    def get_classification_info(class_name: str) -> dict:
        """Get information about a classification class."""
        return {
            "name": class_name,
            "description": CLASSIFICATION_CLASSES.get(class_name, "Unknown class"),
        }

    @staticmethod
    def get_data_type_info(data_type: str) -> dict:
        """Get information about a data type."""
        return {
            "name": data_type,
            "description": DATA_TYPES.get(data_type, "Unknown data type"),
        }


class TestResultAnalyzer:
    """Analyzes test results from JSON reports."""

    def __init__(self, json_report_path: Path):
        """Initialize with path to JSON test report."""
        self.json_path = json_report_path
        self.data = self._load_json()

    def _load_json(self) -> dict:
        """Load JSON report file."""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Report not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_summary(self) -> dict:
        """Get test summary."""
        return self.data.get("summary", {})

    def get_results(self) -> list[dict]:
        """Get all test results."""
        return self.data.get("results", [])

    def get_results_by_status(self, status: str) -> list[dict]:
        """Get results filtered by status (Pass, Fail, Error)."""
        return [r for r in self.get_results() if r.get("status") == status]

    def get_results_by_data_type(self, data_type: str) -> list[dict]:
        """Get results filtered by data type."""
        return [r for r in self.get_results() if r.get("data_type") == data_type]

    def get_failed_tests(self) -> list[dict]:
        """Get all failed tests."""
        return self.get_results_by_status("Fail")

    def get_error_tests(self) -> list[dict]:
        """Get all error tests."""
        return self.get_results_by_status("Error")

    def get_passed_tests(self) -> list[dict]:
        """Get all passed tests."""
        return self.get_results_by_status("Pass")

    def calculate_pass_rate_by_data_type(self) -> dict[str, float]:
        """Calculate pass rate for each data type."""
        rates = {}
        results = self.get_results()

        for data_type in ["Artificial", "Available", "Real"]:
            data_type_results = [r for r in results if r.get("data_type") == data_type]
            if data_type_results:
                passed = sum(
                    1 for r in data_type_results if r.get("status") == "Pass"
                )
                rate = passed / len(data_type_results)
                rates[data_type] = rate

        return rates

    def calculate_pass_rate_by_class(self) -> dict[str, float]:
        """Calculate pass rate for each classification class."""
        rates = {}
        results = self.get_results()

        for class_name in ["Healthy", "Witch Broom", "Unknown"]:
            class_results = [
                r for r in results if r.get("expected_class") == class_name
            ]
            if class_results:
                passed = sum(1 for r in class_results if r.get("status") == "Pass")
                rate = passed / len(class_results)
                rates[class_name] = rate

        return rates

    def generate_summary_report(self) -> str:
        """Generate a text summary report."""
        summary = self.get_summary()
        passed_tests = self.get_passed_tests()
        failed_tests = self.get_failed_tests()
        error_tests = self.get_error_tests()

        report = f"""
================================================================================
TEST RESULTS ANALYSIS - {summary.get('model_type', 'Unknown').upper()} MODEL
================================================================================

OVERVIEW
--------
Total Tests:      {summary.get('total_tests', 0)}
Passed:           {summary.get('passed', 0)}
Failed:           {summary.get('failed', 0)}
Errors:           {summary.get('errors', 0)}
Pass Rate:        {summary.get('pass_rate', 'N/A')}

TIMING
------
Start Time:       {summary.get('start_time', 'N/A')}
End Time:         {summary.get('end_time', 'N/A')}
Duration:         {summary.get('duration_seconds', 0)} seconds

PASS RATE BY DATA TYPE
----------------------
"""
        for data_type, rate in self.calculate_pass_rate_by_data_type().items():
            report += f"{data_type:15} {rate*100:6.1f}%\n"

        report += "\nPASS RATE BY CLASSIFICATION CLASS\n"
        report += "-" * 40 + "\n"
        for class_name, rate in self.calculate_pass_rate_by_class().items():
            report += f"{class_name:15} {rate*100:6.1f}%\n"

        if failed_tests:
            report += "\n\nFAILED TESTS\n"
            report += "-" * 80 + "\n"
            for test in failed_tests:
                report += (
                    f"\n{test['test_case_id']}: {test['input_description'][:50]}...\n"
                )
                report += f"  Expected: {test['expected_class']}\n"
                report += f"  Got:      {test['actual_class']}\n"
                report += f"  Confidence: {test['confidence']}\n"

        if error_tests:
            report += "\n\nERROR TESTS\n"
            report += "-" * 80 + "\n"
            for test in error_tests:
                report += (
                    f"\n{test['test_case_id']}: {test['input_description'][:50]}...\n"
                )
                report += f"  Error: {test['error_message']}\n"

        report += "\n" + "=" * 80 + "\n"

        return report

    def print_summary(self) -> None:
        """Print summary report to console."""
        print(self.generate_summary_report())

    def save_summary(self, filepath: Path) -> None:
        """Save summary report to file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.generate_summary_report())


def compare_test_reports(
    report1_path: Path, report2_path: Path
) -> dict:
    """
    Compare two test reports and identify differences.

    Args:
        report1_path: Path to first report JSON
        report2_path: Path to second report JSON

    Returns:
        Dictionary with comparison results
    """
    analyzer1 = TestResultAnalyzer(report1_path)
    analyzer2 = TestResultAnalyzer(report2_path)

    summary1 = analyzer1.get_summary()
    summary2 = analyzer2.get_summary()

    return {
        "report1": {
            "path": str(report1_path),
            "pass_rate": summary1.get("pass_rate"),
            "total": summary1.get("total_tests"),
            "passed": summary1.get("passed"),
        },
        "report2": {
            "path": str(report2_path),
            "pass_rate": summary2.get("pass_rate"),
            "total": summary2.get("total_tests"),
            "passed": summary2.get("passed"),
        },
        "improvement": {
            "passed_delta": summary2.get("passed", 0) - summary1.get("passed", 0),
            "rate_delta": (
                float(summary2.get("pass_rate", "0%").rstrip("%"))
                - float(summary1.get("pass_rate", "0%").rstrip("%"))
            ),
        },
    }


if __name__ == "__main__":
    from pathlib import Path

    # Example usage
    results_dir = Path(__file__).parent / "test_results"

    # Find the most recent report
    json_files = sorted(results_dir.glob("vision_test_results_*.json"), reverse=True)

    if json_files:
        latest_report = json_files[0]
        print(f"Analyzing: {latest_report.name}\n")

        analyzer = TestResultAnalyzer(latest_report)
        analyzer.print_summary()
