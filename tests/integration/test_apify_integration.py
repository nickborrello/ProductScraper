import pytest
from unittest.mock import AsyncMock
from src.scrapers.master import ProductScraper


@pytest.mark.skip(reason="Skipping apify integration test as some scrapers don't work yet")
@pytest.mark.asyncio
@pytest.mark.skipif(__import__('platform').system() == "Windows", reason="Browser automation unstable on Windows")
async def test_apify_integration_workflow(mocker):
    # Patch the ApifyScraperClient class
    mock_client_class = mocker.patch('src.scrapers.master.ApifyScraperClient')
    
    # Get the mocked instance
    mock_client_instance = mock_client_class.return_value
    
    # Configure the scrape_skus method to be an AsyncMock that calls the progress_callback
    sample_product_data = [
        {
            "SKU": "123456789012",
            "Name": "Sample Product",
            "Price": "19.99",
            "Images": "http://example.com/image1.jpg,http://example.com/image2.jpg",
            "Weight": "5.0 LB",
            "Brand": "Sample Brand"
        }
    ]
    
    def mock_scrape_skus(site, skus, progress_callback=None):
        if progress_callback:
            progress_callback("SUCCEEDED")  # Simulate calling the progress callback
        return sample_product_data
    
    mock_client_instance.scrape_skus = AsyncMock(side_effect=mock_scrape_skus)
    
    # Create a mock progress_callback
    mock_progress_callback = mocker.MagicMock()
    
    # Instantiate the ProductScraper with minimal required parameters
    # For testing, we'll use a temporary file path and non-interactive mode
    import tempfile
    import pandas as pd
    
    # Create a temporary input file with test data
    test_data = {
        "SKU": ["123456789012"],
        "Name": ["Test Product"],
        "Price": ["19.99"]
    }
    df = pd.DataFrame(test_data)
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
        df.to_excel(temp_file.name, index=False)
        temp_file_path = temp_file.name
    
    try:
        # Instantiate ProductScraper
        scraper = ProductScraper(
            file_path=temp_file_path,
            interactive=False,  # Non-interactive for testing
            log_callback=print,
            progress_callback=mock_progress_callback
        )
        
        # Call the main asynchronous scraping method
        await scraper.scrape()
        
        # Assert that the mocked scrape_skus was called
        mock_client_instance.scrape_skus.assert_called()
        
        # Assert that the progress_callback was called (confirming UI hook is connected)
        mock_progress_callback.assert_called()
        
        # Note: In a full integration test, we might also check that data was saved
        # But for this test, we're primarily verifying the workflow and mocking
        
    finally:
        # Clean up temporary file
        import os
        os.unlink(temp_file_path)