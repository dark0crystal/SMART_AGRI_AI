"""
Django management command to run AI model tests.

Usage:
    python manage.py run_ai_tests [options]
    python manage.py run_ai_tests --vision --text
    python manage.py run_ai_tests --vision-only
    python manage.py run_ai_tests --analyze reports/vision_test_results_*.json
"""

import sys
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

# Add parent directories to path
backend_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))


class Command(BaseCommand):
    help = "Run SMART AGRI AI model unit tests"

    def add_arguments(self, parser):
        parser.add_argument(
            "--vision",
            action="store_true",
            help="Run vision model tests",
        )
        parser.add_argument(
            "--text",
            action="store_true",
            help="Run text model tests",
        )
        parser.add_argument(
            "--vision-only",
            action="store_true",
            help="Run only vision model tests (shortcut for --vision without --text)",
        )
        parser.add_argument(
            "--text-only",
            action="store_true",
            help="Run only text model tests (shortcut for --text without --vision)",
        )
        parser.add_argument(
            "--analyze",
            type=str,
            help="Analyze existing test report file (JSON path)",
        )
        parser.add_argument(
            "--compare",
            nargs=2,
            metavar=("REPORT1", "REPORT2"),
            help="Compare two test reports",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Custom output directory for test results",
        )
        parser.add_argument(
            "--generate-images-only",
            action="store_true",
            help="Only generate test images without running tests",
        )

    def handle(self, *args, **options):
        try:
            # Handle analysis modes
            if options["analyze"]:
                self.analyze_report(options["analyze"])
                return

            if options["compare"]:
                self.compare_reports(options["compare"])
                return

            # Determine which tests to run
            run_vision = options["vision"] or options["vision_only"] or (
                not options["text"] and not options["text_only"]
            )
            run_text = options["text"] or options["text_only"] or (
                not options["vision"] and not options["vision_only"]
            )

            # If only generating images
            if options["generate_images_only"]:
                self.generate_test_images()
                return

            # Run tests
            from tests.test_runner import AIModelTestRunner

            results_dir = None
            if options["output_dir"]:
                results_dir = Path(options["output_dir"])

            runner = AIModelTestRunner(results_dir=results_dir)

            if run_vision:
                self.stdout.write(self.style.SUCCESS("Running vision model tests..."))
                runner.run_vision_tests()

            if run_text:
                self.stdout.write(self.style.SUCCESS("Running text model tests..."))
                runner.run_text_tests()

            # Generate reports
            self.stdout.write(self.style.SUCCESS("Generating test reports..."))
            runner.generate_reports()

            # Print summary
            runner.print_summary()

            self.stdout.write(
                self.style.SUCCESS("✓ All tests completed successfully!")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test execution failed: {str(e)}"))
            raise CommandError(str(e))

    def generate_test_images(self):
        """Generate test images only."""
        from tests.test_data_generator import create_test_images

        images_dir = Path(__file__).parent.parent / "test_data" / "vision_images"

        self.stdout.write(f"Creating test images in {images_dir}...")
        created = create_test_images(images_dir)

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(created)} test images:"))
        for tc_id, path in created.items():
            self.stdout.write(f"  {tc_id}: {path}")

    def analyze_report(self, report_path: str):
        """Analyze a test report."""
        from tests.test_utils import TestResultAnalyzer

        path = Path(report_path)

        if not path.exists():
            raise CommandError(f"Report file not found: {report_path}")

        try:
            analyzer = TestResultAnalyzer(path)
            analyzer.print_summary()

            self.stdout.write(
                self.style.SUCCESS(f"✓ Analysis complete for {path.name}")
            )
        except Exception as e:
            raise CommandError(f"Failed to analyze report: {str(e)}")

    def compare_reports(self, reports: list[str]):
        """Compare two test reports."""
        from tests.test_utils import compare_test_reports

        report1_path = Path(reports[0])
        report2_path = Path(reports[1])

        if not report1_path.exists():
            raise CommandError(f"Report not found: {reports[0]}")
        if not report2_path.exists():
            raise CommandError(f"Report not found: {reports[1]}")

        try:
            comparison = compare_test_reports(report1_path, report2_path)

            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("TEST REPORT COMPARISON")
            self.stdout.write("=" * 80)

            self.stdout.write(f"\nReport 1: {comparison['report1']['path']}")
            self.stdout.write(f"  Total: {comparison['report1']['total']}")
            self.stdout.write(f"  Passed: {comparison['report1']['passed']}")
            self.stdout.write(f"  Pass Rate: {comparison['report1']['pass_rate']}")

            self.stdout.write(f"\nReport 2: {comparison['report2']['path']}")
            self.stdout.write(f"  Total: {comparison['report2']['total']}")
            self.stdout.write(f"  Passed: {comparison['report2']['passed']}")
            self.stdout.write(f"  Pass Rate: {comparison['report2']['pass_rate']}")

            improvement = comparison["improvement"]["passed_delta"]
            rate_improvement = comparison["improvement"]["rate_delta"]

            self.stdout.write(f"\nImprovement:")
            if improvement >= 0:
                self.stdout.write(
                    self.style.SUCCESS(f"  Passed Tests: +{improvement}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  Passed Tests: {improvement}")
                )

            if rate_improvement >= 0:
                self.stdout.write(
                    self.style.SUCCESS(f"  Pass Rate: +{rate_improvement:.1f}%")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  Pass Rate: {rate_improvement:.1f}%")
                )

            self.stdout.write("=" * 80 + "\n")

        except Exception as e:
            raise CommandError(f"Failed to compare reports: {str(e)}")
