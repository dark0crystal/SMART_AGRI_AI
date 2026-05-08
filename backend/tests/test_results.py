"""
Comprehensive test runner for SMART AGRI AI models.
Executes vision and text model tests and generates result reports.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from abc import ABC, abstractmethod

from PIL import Image

logger = logging.getLogger(__name__)


class TestResult:
    """Represents a single test execution result."""

    def __init__(
        self,
        test_case_id: str,
        data_type: str,
        input_description: str,
        expected_class: str,
        actual_class: Optional[str] = None,
        confidence: Optional[float] = None,
        status: str = "Pending",
        error_message: Optional[str] = None,
    ):
        self.test_case_id = test_case_id
        self.data_type = data_type
        self.input_description = input_description
        self.expected_class = expected_class
        self.actual_class = actual_class
        self.confidence = confidence
        self.status = status  # Pass, Fail, Error
        self.error_message = error_message
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "test_case_id": self.test_case_id,
            "data_type": self.data_type,
            "input_description": self.input_description,
            "expected_class": self.expected_class,
            "actual_class": self.actual_class or "N/A",
            "confidence": f"{self.confidence:.2%}" if self.confidence else "N/A",
            "status": self.status,
            "error_message": self.error_message or "",
            "timestamp": self.timestamp,
        }

    def to_csv_row(self) -> dict:
        """Convert to CSV row format."""
        return {
            "Test Case ID": self.test_case_id,
            "Data Type": self.data_type,
            "Input Description": self.input_description,
            "Expected Class": self.expected_class,
            "Actual Class": self.actual_class or "N/A",
            "Confidence": f"{self.confidence:.2%}" if self.confidence else "N/A",
            "Status": self.status,
            "Error": self.error_message or "",
        }


class TestSuite:
    """Manages a suite of test results."""

    def __init__(self, model_type: str):
        self.model_type = model_type  # "vision" or "text"
        self.results: list[TestResult] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self.results.append(result)

    def get_summary(self) -> dict:
        """Get test suite summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "Pass")
        failed = sum(1 for r in self.results if r.status == "Fail")
        errors = sum(1 for r in self.results if r.status == "Error")

        return {
            "model_type": self.model_type,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time
                else None
            ),
        }

    def save_csv(self, filepath: Path) -> None:
        """Save results to CSV file."""
        if not self.results:
            logger.warning(f"No results to save for {self.model_type}")
            return

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "Test Case ID",
                "Data Type",
                "Input Description",
                "Expected Class",
                "Actual Class",
                "Confidence",
                "Status",
                "Error",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.results:
                writer.writerow(result.to_csv_row())

        logger.info(f"Results saved to {filepath}")

    def save_json(self, filepath: Path) -> None:
        """Save results to JSON file."""
        if not self.results:
            logger.warning(f"No results to save for {self.model_type}")
            return

        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {filepath}")

    def save_html_report(self, filepath: Path) -> None:
        """Generate and save an HTML report."""
        filepath.parent.mkdir(parents=True, exist_ok=True)

        summary = self.get_summary()
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>SMART AGRI AI - {self.model_type.upper()} Model Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #27ae60; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ background-color: #ecf0f1; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        .summary-item-label {{ font-weight: bold; color: #34495e; }}
        .summary-item-value {{ font-size: 1.3em; color: #27ae60; }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
        .error {{ color: #f39c12; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background-color: #34495e; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #bdc3c7; }}
        tr:hover {{ background-color: #f8f9fa; }}
        .timestamp {{ color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>SMART AGRI AI - {self.model_type.upper()} Model Test Report</h1>
        
        <div class="summary">
            <h2>Test Summary</h2>
            <div class="summary-item">
                <div class="summary-item-label">Total Tests:</div>
                <div class="summary-item-value">{summary['total_tests']}</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Passed:</div>
                <div class="summary-item-value pass">{summary['passed']}</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Failed:</div>
                <div class="summary-item-value fail">{summary['failed']}</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Errors:</div>
                <div class="summary-item-value error">{summary['errors']}</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Pass Rate:</div>
                <div class="summary-item-value">{summary['pass_rate']}</div>
            </div>
            <p class="timestamp">Generated: {summary['start_time']}</p>
        </div>

        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Case ID</th>
                    <th>Data Type</th>
                    <th>Input Description</th>
                    <th>Expected Class</th>
                    <th>Actual Class</th>
                    <th>Confidence</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""

        for result in self.results:
            status_class = result.status.lower()
            html_content += f"""                <tr>
                    <td><strong>{result.test_case_id}</strong></td>
                    <td>{result.data_type}</td>
                    <td>{result.input_description[:50]}...</td>
                    <td>{result.expected_class}</td>
                    <td>{result.actual_class or 'N/A'}</td>
                    <td>{f'{result.confidence:.1%}' if result.confidence else 'N/A'}</td>
                    <td><span class="{status_class}">{result.status}</span></td>
                </tr>
"""

        html_content += """            </tbody>
        </table>
    </div>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML report saved to {filepath}")

    def finalize(self) -> None:
        """Mark test suite as complete."""
        self.end_time = datetime.now()
