#!/usr/bin/env python3
"""
Flavor Integration Test Suite Runner

Automated test runner for comprehensive Flavor integration testing.
Orchestrates all integration tests and provides detailed reporting.
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

# Import our test frameworks
sys.path.append(str(Path(__file__).parent))
from test_flavor_integration_comprehensive import FlavorTestFramework
from test_flavor_error_handling import FlavorErrorTestFramework
from test_terraform_flavor_integration import TerraformFlavorTestFramework

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Data class for test results"""
    name: str
    success: bool
    message: str
    duration: float
    category: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class TestSuiteReport:
    """Data class for test suite report"""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    total_duration: float
    results: List[TestResult]
    environment: Dict[str, str]

class FlavorIntegrationTestRunner:
    """Comprehensive integration test runner for Flavor system"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.project_root = Path("/REDACTED_ABS_PATH")
        self.output_dir = output_dir or Path("/tmp/flavor_test_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize test frameworks
        self.frameworks = {
            "comprehensive": FlavorTestFramework(),
            "error_handling": FlavorErrorTestFramework(),
            "terraform": TerraformFlavorTestFramework()
        }
        
        # Test results
        self.results: List[TestResult] = []
        
    def run_test(self, test_name: str, test_func, category: str, *args, **kwargs) -> TestResult:
        """Run a single test and capture results"""
        logger.info(f"Running test: {test_name}")
        
        start_time = time.perf_counter()
        
        try:
            if hasattr(test_func, '__call__'):
                result = test_func(*args, **kwargs)
                
                # Handle different return formats
                if isinstance(result, tuple):
                    if len(result) == 2:
                        success, message = result
                        details = None
                    elif len(result) == 3:
                        success, message, details = result
                    else:
                        success, message = result[0], result[1]
                        details = {"extra": result[2:]} if len(result) > 2 else None
                else:
                    success = bool(result)
                    message = "Test completed"
                    details = None
                
        except Exception as e:
            success = False
            message = f"Test error: {str(e)}"
            details = {"exception": str(e)}
            logger.exception(f"Test {test_name} raised exception")
            
        duration = time.perf_counter() - start_time
        
        test_result = TestResult(
            name=test_name,
            success=success,
            message=message,
            duration=duration,
            category=category,
            details=details
        )
        
        self.results.append(test_result)
        
        status = "PASS" if success else "FAIL"
        logger.info(f"Test {test_name}: {status} ({duration:.2f}s) - {message}")
        
        return test_result

    def run_comprehensive_tests(self) -> List[TestResult]:
        """Run comprehensive Flavor tests"""
        logger.info("=== Running Comprehensive Flavor Tests ===")
        
        framework = self.frameworks["comprehensive"]
        test_dirs = framework.setup_test_environment()
        
        try:
            tests = [
                ("Package Creation", framework.test_package_creation),
                ("Package Verification", framework.test_package_verification),
                ("Launch Context Detection", framework.test_launch_context_detection),
                ("Terraform Integration", framework.test_terraform_integration),
            ]
            
            results = []
            for test_name, test_func in tests:
                result = self.run_test(
                    f"Comprehensive - {test_name}",
                    test_func,
                    "comprehensive",
                    test_dirs
                )
                results.append(result)
                
            # Run launcher tests
            for launcher_type in framework.test_launchers:
                launcher_path = Path(framework.test_launchers[launcher_type])
                if launcher_path.exists():
                    result = self.run_test(
                        f"Comprehensive - {launcher_type.title()} Launcher Extraction",
                        framework.test_launcher_extraction,
                        "comprehensive",
                        launcher_type,
                        test_dirs
                    )
                    results.append(result)
                else:
                    # Record skipped test
                    result = TestResult(
                        name=f"Comprehensive - {launcher_type.title()} Launcher Extraction",
                        success=True,
                        message=f"Skipped - {launcher_type} launcher not found",
                        duration=0.0,
                        category="comprehensive",
                        details={"skipped": True}
                    )
                    self.results.append(result)
                    results.append(result)
                    
            return results
            
        finally:
            framework.cleanup_test_environment(test_dirs)

    def run_error_handling_tests(self) -> List[TestResult]:
        """Run error handling and edge case tests"""
        logger.info("=== Running Error Handling Tests ===")
        
        framework = self.frameworks["error_handling"]
        
        # Corruption tests
        corruption_tests = [
            ("invalid_magic", "not a flavor file"),
            ("invalid_footer_magic", "invalid footer magic"),
            ("truncated_file", "read"),
            ("empty_file", "not a flavor file"),
            ("wrong_launcher", "not a flavor file"),
        ]
        
        results = []
        
        for corruption_type, expected_error in corruption_tests:
            result = self.run_test(
                f"Error Handling - Corruption ({corruption_type})",
                framework.test_corrupted_package_handling,
                "error_handling",
                corruption_type,
                expected_error
            )
            results.append(result)
            
        # Other error tests
        error_tests = [
            ("Permission Errors", framework.test_permission_errors),
            ("Concurrent Extraction", framework.test_concurrent_extraction),
            ("CLI Arguments", framework.test_malformed_command_line_args),
        ]
        
        for test_name, test_func in error_tests:
            result = self.run_test(
                f"Error Handling - {test_name}",
                test_func,
                "error_handling"
            )
            results.append(result)
            
        return results

    def run_terraform_tests(self) -> List[TestResult]:
        """Run Terraform integration tests"""
        logger.info("=== Running Terraform Integration Tests ===")
        
        framework = self.frameworks["terraform"]
        
        # Check for Flavor package
        package_path = self.project_root / "terraform-provider-pyvider" / "dist" / "flavor" / "darwin_arm64" / "terraform-provider-pyvider_v0.0.1"
        
        if not package_path.exists():
            # Record skipped tests
            terraform_test_names = [
                "Init", "Plan (Data Source)", "Plan (Resource)", 
                "Plan (Functions)", "Apply/Destroy", "State Management", 
                "Launch Context Logging"
            ]
            
            results = []
            for test_name in terraform_test_names:
                result = TestResult(
                    name=f"Terraform - {test_name}",
                    success=True,
                    message="Skipped - Flavor package not found",
                    duration=0.0,
                    category="terraform",
                    details={"skipped": True}
                )
                self.results.append(result)
                results.append(result)
                
            return results
        
        tests = [
            ("Init", framework.test_terraform_init_with_flavor),
            ("Plan (Data Source)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "data_source_test")),
            ("Plan (Resource)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "resource_test")),
            ("Plan (Functions)", lambda pkg: framework.test_terraform_plan_with_flavor(pkg, "function_test")),
            ("Apply/Destroy", framework.test_terraform_apply_with_flavor),
            ("State Management", framework.test_terraform_state_management_with_flavor),
            ("Launch Context Logging", lambda pkg: framework.test_launch_context_in_terraform_logs(pkg)),
        ]
        
        results = []
        for test_name, test_func in tests:
            result = self.run_test(
                f"Terraform - {test_name}",
                test_func,
                "terraform",
                package_path
            )
            results.append(result)
            
        return results

    def run_all_tests(self) -> TestSuiteReport:
        """Run all integration tests"""
        logger.info("Starting Flavor Integration Test Suite")
        start_time = time.perf_counter()
        
        # Clear previous results
        self.results = []
        
        # Run test suites
        try:
            comprehensive_results = self.run_comprehensive_tests()
        except Exception as e:
            logger.exception("Comprehensive tests failed")
            comprehensive_results = []
            
        try:
            error_results = self.run_error_handling_tests()
        except Exception as e:
            logger.exception("Error handling tests failed")
            error_results = []
            
        try:
            terraform_results = self.run_terraform_tests()
        except Exception as e:
            logger.exception("Terraform tests failed")
            terraform_results = []
        
        total_duration = time.perf_counter() - start_time
        
        # Generate report
        passed = sum(1 for r in self.results if r.success and not (r.details and isinstance(r.details, dict) and r.details.get("skipped", False)))
        failed = sum(1 for r in self.results if not r.success and not (r.details and isinstance(r.details, dict) and r.details.get("skipped", False)))
        skipped = sum(1 for r in self.results if r.details and isinstance(r.details, dict) and r.details.get("skipped", False))
        
        report = TestSuiteReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            total_duration=total_duration,
            results=self.results,
            environment={
                "python_version": sys.version,
                "platform": sys.platform,
                "project_root": str(self.project_root),
                "test_runner_version": "1.0.0"
            }
        )
        
        return report

    def generate_report(self, report: TestSuiteReport, format: str = "both") -> Dict[str, Path]:
        """Generate test report in various formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        generated_files = {}
        
        # JSON Report
        if format in ["json", "both"]:
            json_file = self.output_dir / f"flavor_integration_test_report_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            generated_files["json"] = json_file
            logger.info(f"JSON report generated: {json_file}")
        
        # HTML Report
        if format in ["html", "both"]:
            html_file = self.output_dir / f"flavor_integration_test_report_{timestamp}.html"
            self._generate_html_report(report, html_file)
            generated_files["html"] = html_file
            logger.info(f"HTML report generated: {html_file}")
            
        return generated_files

    def _generate_html_report(self, report: TestSuiteReport, output_file: Path) -> None:
        """Generate HTML report"""
        
        # Calculate statistics by category
        categories = {}
        for result in report.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}
            
            categories[result.category]["total"] += 1
            if result.details and isinstance(result.details, dict) and result.details.get("skipped", False):
                categories[result.category]["skipped"] += 1
            elif result.success:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Flavor Integration Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .category {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .category-header {{ background-color: #e9ecef; padding: 10px; font-weight: bold; }}
        .test-result {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .test-result:last-child {{ border-bottom: none; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .skip {{ color: #6c757d; }}
        .duration {{ color: #666; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Flavor Integration Test Report</h1>
        <p><strong>Generated:</strong> {report.timestamp}</p>
        <p><strong>Total Duration:</strong> {report.total_duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>Test Summary</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Skipped</th>
                <th>Success Rate</th>
            </tr>
"""
        
        for category, stats in categories.items():
            success_rate = (stats["passed"] / (stats["total"] - stats["skipped"]) * 100) if (stats["total"] - stats["skipped"]) > 0 else 0
            html_content += f"""
            <tr>
                <td>{category.title()}</td>
                <td>{stats["total"]}</td>
                <td class="pass">{stats["passed"]}</td>
                <td class="fail">{stats["failed"]}</td>
                <td class="skip">{stats["skipped"]}</td>
                <td>{success_rate:.1f}%</td>
            </tr>
"""
        
        html_content += f"""
        </table>
        
        <h3>Overall Statistics</h3>
        <ul>
            <li><strong>Total Tests:</strong> {report.total_tests}</li>
            <li><strong class="pass">Passed:</strong> {report.passed}</li>
            <li><strong class="fail">Failed:</strong> {report.failed}</li>
            <li><strong class="skip">Skipped:</strong> {report.skipped}</li>
            <li><strong>Success Rate:</strong> {(report.passed / (report.total_tests - report.skipped) * 100) if (report.total_tests - report.skipped) > 0 else 0:.1f}%</li>
        </ul>
    </div>
    
    <h2>Test Details</h2>
"""
        
        # Group results by category
        for category, stats in categories.items():
            html_content += f"""
    <div class="category">
        <div class="category-header">{category.title()} Tests</div>
"""
            
            category_results = [r for r in report.results if r.category == category]
            for result in category_results:
                status_class = "skip" if result.details and isinstance(result.details, dict) and result.details.get("skipped", False) else ("pass" if result.success else "fail")
                status_text = "SKIP" if result.details and isinstance(result.details, dict) and result.details.get("skipped", False) else ("PASS" if result.success else "FAIL")
                
                html_content += f"""
        <div class="test-result">
            <strong class="{status_class}">{status_text}</strong> {result.name}
            <span class="duration">({result.duration:.2f}s)</span>
            <br>
            <em>{result.message}</em>
        </div>
"""
            
            html_content += "    </div>"
        
        html_content += """
</body>
</html>
"""
        
        output_file.write_text(html_content)

    def print_summary(self, report: TestSuiteReport) -> None:
        """Print test summary to console"""
        print("\n" + "="*60)
        print("Flavor INTEGRATION TEST SUITE SUMMARY")
        print("="*60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Duration: {report.total_duration:.2f} seconds")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed}")
        print(f"Failed: {report.failed}")
        print(f"Skipped: {report.skipped}")
        
        if report.total_tests - report.skipped > 0:
            success_rate = report.passed / (report.total_tests - report.skipped) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in report.results if not r.success and not (r.details and isinstance(r.details, dict) and r.details.get("skipped", False))]
        if failed_tests:
            print(f"\nFAILED TESTS ({len(failed_tests)}):")
            for result in failed_tests:
                print(f"  ❌ {result.name}: {result.message}")
        
        # Print category breakdown
        categories = {}
        for result in report.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0, "skipped": 0}
            
            if result.details and isinstance(result.details, dict) and result.details.get("skipped", False):
                categories[result.category]["skipped"] += 1
            elif result.success:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
        
        print(f"\nCATEGORY BREAKDOWN:")
        for category, stats in categories.items():
            total = sum(stats.values())
            print(f"  {category.title()}: {stats['passed']} passed, {stats['failed']} failed, {stats['skipped']} skipped ({total} total)")
        
        print("="*60)

def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description="Flavor Integration Test Suite Runner")
    parser.add_argument("--output-dir", type=Path, help="Output directory for reports")
    parser.add_argument("--format", choices=["json", "html", "both"], default="both", help="Report format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create test runner
    runner = FlavorIntegrationTestRunner(output_dir=args.output_dir)
    
    try:
        # Run all tests
        report = runner.run_all_tests()
        
        # Generate reports
        generated_files = runner.generate_report(report, format=args.format)
        
        # Print summary
        runner.print_summary(report)
        
        # Print generated file paths
        if generated_files:
            print(f"\nREPORTS GENERATED:")
            for format_type, file_path in generated_files.items():
                print(f"  {format_type.upper()}: {file_path}")
        
        # Exit with non-zero if tests failed
        if report.failed > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Test runner error")
        print(f"\nTest runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


# 📦🍜🧪🪄
