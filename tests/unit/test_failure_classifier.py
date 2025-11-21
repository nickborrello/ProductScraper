"""
Unit tests for FailureClassifier NO_RESULTS detection
"""

from unittest.mock import MagicMock, Mock

import pytest

from src.core.failure_classifier import FailureClassifier, FailureType


class TestFailureClassifierNoResults:
    """Test NO_RESULTS detection in FailureClassifier."""

    @pytest.fixture
    def classifier(self):
        """Fixture for FailureClassifier instance."""
        return FailureClassifier()

    @pytest.fixture
    def mock_driver(self):
        """Fixture for mocked WebDriver."""
        driver = MagicMock()
        driver.page_source = ""
        driver.title = ""
        driver.find_elements.return_value = []
        return driver

    def test_no_results_selectors_detection(self, classifier, mock_driver):
        """Test detection of NO_RESULTS via CSS selectors."""
        # Test with no-results class selector
        mock_driver.find_elements.side_effect = (
            lambda by, selector: [
                Mock()  # Return element for no-results selector
            ]
            if selector == "[class*='no-results']"
            else []
        )
        high_confidence_threshold = 0.8
        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.NO_RESULTS
        assert result.confidence == high_confidence_threshold  # High confidence for selector match
        assert result.recovery_strategy == "fail_and_continue_to_next_sku"

    def test_no_results_text_patterns_detection(self, classifier, mock_driver):
        """Test detection of NO_RESULTS via text patterns."""
        # Use content that matches multiple patterns to exceed 0.3 confidence threshold
        mock_driver.page_source = (
            "<html><body>No results found. Your search returned no results. No matching products "
            "found.</body></html>"
        )
        mock_driver.title = "Search Results"
        min_confidence_threshold = 0.3
        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence > min_confidence_threshold
        )  # Should exceed threshold with multiple matches
        assert result.details["text_match"] is True

    def test_no_results_title_patterns_detection(self, classifier, mock_driver):
        """Test detection of NO_RESULTS via title patterns."""
        mock_driver.page_source = "<html><body>Some content</body></html>"
        # Use title that matches multiple patterns to exceed threshold
        mock_driver.title = "No Results Found - No Matching Products"
        min_confidence_threshold = 0.5
        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= min_confidence_threshold
        )  # Title match with reduced weight but multiple patterns, and now better classification
        assert result.details["title_match"] is True

    def test_no_results_multiple_patterns_confidence(self, classifier, mock_driver):
        """Test confidence scoring with multiple NO_RESULTS patterns."""
        high_confidence_threshold = 0.8

        # Mock multiple selector matches
        def find_elements_side_effect(by, selector):
            if selector in ["[class*='no-results']", ".no-products"]:
                return [Mock()]
            return []

        mock_driver.find_elements.side_effect = find_elements_side_effect
        mock_driver.page_source = "<html><body>No matching products found</body></html>"

        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= high_confidence_threshold
        )  # High confidence from multiple matches

    def test_no_results_partial_text_match(self, classifier, mock_driver):
        """Test partial text matches for NO_RESULTS."""
        mock_driver.page_source = (
            "<html><body>Your search returned no results. No matching products found.</body></html>"
        )
        min_confidence_threshold = 0.5
        result = classifier.classify_page_content(mock_driver, {})
        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= min_confidence_threshold
        )  # Should exceed threshold with multiple matches and now better classification

    def test_no_results_case_insensitive_matching(self, classifier, mock_driver):
        """Test case-insensitive text pattern matching."""
        mock_driver.page_source = (
            "<html><body>NO RESULTS FOUND. NO MATCHING PRODUCTS FOUND.</body></html>"
        )
        min_confidence_threshold = 0.5
        result = classifier.classify_page_content(mock_driver, {})
        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= min_confidence_threshold
        )  # Should exceed threshold and now better classification

    def test_no_results_false_positive_avoidance(self, classifier, mock_driver):
        """Test avoiding false positives for NO_RESULTS."""
        # Content that might trigger partial matches but shouldn't
        mock_driver.page_source = "<html><body>This product has no special results</body></html>"
        low_confidence_threshold = 0.3
        result = classifier.classify_page_content(mock_driver, {})

        # Should not classify as NO_RESULTS due to low confidence
        assert (
            result.failure_type != FailureType.NO_RESULTS
            or result.confidence < low_confidence_threshold
        )

    def test_no_results_vs_other_failure_types(self, classifier, mock_driver):
        """Test differentiation between NO_RESULTS and other failure types."""
        # Test CAPTCHA content that should clearly match CAPTCHA patterns
        mock_driver.page_source = (
            "<html><body>Please verify you are human. Complete the captcha to "
            "continue.</body></html>"
        )

        result = classifier.classify_page_content(mock_driver, {})

        # Should classify as CAPTCHA due to multiple pattern matches
        assert result.failure_type == FailureType.CAPTCHA_DETECTED
        assert result.failure_type != FailureType.NO_RESULTS

    def test_no_results_with_login_failure_content(self, classifier, mock_driver):
        """Test NO_RESULTS doesn't trigger on login failure content."""
        mock_driver.page_source = "<html><body>Login failed - incorrect credentials</body></html>"

        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.LOGIN_FAILED
        assert result.failure_type != FailureType.NO_RESULTS

    def test_no_results_empty_selectors_list(self, classifier, mock_driver):
        """Test behavior when no selectors match."""
        mock_driver.find_elements.return_value = []  # No elements found
        mock_driver.page_source = "<html><body>Regular product page content</body></html>"
        low_confidence_threshold = 0.3
        result = classifier.classify_page_content(mock_driver, {})

        # Should not classify as NO_RESULTS with high confidence
        assert result.confidence < low_confidence_threshold

    def test_no_results_selector_exception_handling(self, classifier, mock_driver):
        """Test handling of exceptions during selector checking."""
        mock_driver.find_elements.side_effect = Exception("Selector error")
        # Use content that matches multiple patterns to exceed threshold
        mock_driver.page_source = (
            "<html><body>No results found. No matching products found.</body></html>"
        )
        min_confidence_threshold = 0.5
        result = classifier.classify_page_content(mock_driver, {})

        # Should still work via text patterns despite selector exception
        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= min_confidence_threshold
        )  # Should still work via text patterns despite selector exception, with better confidence

    def test_no_results_text_pattern_confidence_calculation(self, classifier):
        """Test confidence calculation for text pattern matching."""
        patterns = [
            r"no (results?|products?) found",
            r"your search.*returned no results",
            r"no matching products",
        ]
        fixed_confidence = 0.7
        min_confidence = 0.0
        # Test single match
        confidence = classifier._calculate_text_match_confidence("no results found", patterns)
        assert confidence == fixed_confidence  # Fixed confidence for any match

        # Test multiple matches still returns the fixed confidence
        confidence = classifier._calculate_text_match_confidence(
            "no results found - your search returned no results", patterns
        )
        assert confidence == fixed_confidence  # Should still be the fixed confidence

        # Test no matches
        confidence = classifier._calculate_text_match_confidence("regular content", patterns)
        assert confidence == min_confidence

    def test_no_results_integration_with_page_content(self, classifier, mock_driver):
        """Test full integration of NO_RESULTS detection with page content analysis."""
        # Simulate a realistic no-results page
        mock_driver.page_source = """
        <html>
        <head><title>No Results Found - Product Search</title></head>
        <body>
            <div class="no-results">
                <h1>No products found</h1>
                <p>Your search for "nonexistent product" returned no results.</p>
                <p>Please try a different search term.</p>
            </div>
        </body>
        </html>
        """
        mock_driver.title = "No Results Found - Product Search"
        high_confidence_threshold = 0.8
        # Mock selector match
        mock_driver.find_elements.side_effect = (
            lambda by, selector: [Mock()] if selector == "[class*='no-results']" else []
        )

        result = classifier.classify_page_content(mock_driver, {})

        assert result.failure_type == FailureType.NO_RESULTS
        assert (
            result.confidence >= high_confidence_threshold
        )  # High confidence from multiple indicators and new logic
        assert result.details["selector_match"] is True
        assert result.details["text_match"] is True
        assert result.details["title_match"] is True
        assert result.recovery_strategy == "fail_and_continue_to_next_sku"

    def test_no_results_edge_case_empty_page(self, classifier, mock_driver):
        """Test NO_RESULTS detection on empty or minimal page content."""
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = ""
        low_confidence_threshold = 0.3
        result = classifier.classify_page_content(mock_driver, {})

        # Should not classify as NO_RESULTS with high confidence
        assert result.confidence < low_confidence_threshold

    def test_no_results_edge_case_similar_text(self, classifier, mock_driver):
        """Test edge case with text that contains NO_RESULTS keywords but isn't actually no results."""
        mock_driver.page_source = """
        <html><body>
            <p>This product has no special results or features.</p>
            <p>No additional results were found in the database.</p>
            <p>The search completed with no errors.</p>
        </body></html>
        """
        min_confidence_threshold = 0.5
        result = classifier.classify_page_content(mock_driver, {})

        # Should have low confidence due to partial matches not forming complete patterns
        assert result.confidence < min_confidence_threshold

    def test_no_results_with_status_code_context(self, classifier, mock_driver):
        """Test NO_RESULTS detection with HTTP status code context."""
        # Use content that triggers NO_RESULTS
        mock_driver.page_source = (
            "<html><body>No results found. No matching products found.</body></html>"
        )
        status_code = 404
        high_confidence = 0.95
        # High-confidence status codes take precedence over content-based detection
        result = classifier.classify_page_content(mock_driver, {"status_code": status_code})

        # 404 status code gives very high confidence to PAGE_NOT_FOUND
        assert result.failure_type == FailureType.PAGE_NOT_FOUND
        assert result.confidence == high_confidence
        assert result.details["status_code_match"] == status_code

    def test_no_results_confidence_threshold(self, classifier, mock_driver):
        """Test that NO_RESULTS requires sufficient confidence threshold."""
        # Very weak match
        mock_driver.page_source = "<html><body>no</body></html>"
        low_confidence_threshold = 0.3
        result = classifier.classify_page_content(mock_driver, {})

        # Should not classify as NO_RESULTS due to low confidence
        assert (
            result.failure_type != FailureType.NO_RESULTS
            or result.confidence < low_confidence_threshold
        )
