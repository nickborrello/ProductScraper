import pytest
import pytest_mock
from src.core.scrapers.apify_client import ApifyScraperClient, ApifyAuthError, ApifyTimeoutError, ApifyJobError


@pytest.mark.asyncio
async def test_scrape_skus_success(mocker):
    # Mock the httpx.AsyncClient
    mock_client = mocker.AsyncMock()
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    # Mock SettingsManager
    mock_settings = mocker.Mock()
    mock_settings.get.side_effect = lambda key: {
        'apify_api_token': 'test_token',
        'apify_base_url': 'https://api.apify.com/v2'
    }.get(key)
    mocker.patch('src.core.scrapers.apify_client.SettingsManager', return_value=mock_settings)
    
    client = ApifyScraperClient()
    
    # Mock responses
    run_response = mocker.Mock()
    run_response.is_success = True
    run_response.json.return_value = {"data": {"id": "test_run_id"}}
    
    running_response = mocker.Mock()
    running_response.is_success = True
    running_response.json.return_value = {"data": {"status": "RUNNING"}}
    
    success_response = mocker.Mock()
    success_response.is_success = True
    success_response.json.return_value = {"data": {"status": "SUCCEEDED", "defaultDatasetId": "test_dataset_id"}}
    
    dataset_response = mocker.Mock()
    dataset_response.is_success = True
    dataset_response.json.return_value = [
        {
            "sku": "12345",
            "product_name": "Test Product",
            "price": "19.99",
            "images": "img1.jpg,img2.jpg",
            "weight": "1.5 LB",
            "brand": "Test Brand"
        }
    ]
    
    # Sequence: post (start), get (running), get (running), get (succeeded), get (dataset)
    mock_client.post.side_effect = [run_response]
    mock_client.get.side_effect = [running_response, running_response, success_response, dataset_response]
    
    result = await client.scrape_skus("test_site", ["12345"])
    
    expected = [
        {
            "SKU": "12345",
            "Name": "Test Product",
            "Price": "19.99",
            "Images": "img1.jpg,img2.jpg",
            "Weight": "1.5 LB",
            "Brand": "Test Brand"
        }
    ]
    assert result == expected


@pytest.mark.asyncio
async def test_scrape_skus_job_failure(mocker):
    mock_client = mocker.AsyncMock()
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    mock_settings = mocker.Mock()
    mock_settings.get.side_effect = lambda key: {
        'apify_api_token': 'test_token',
        'apify_base_url': 'https://api.apify.com/v2'
    }.get(key)
    mocker.patch('src.core.scrapers.apify_client.SettingsManager', return_value=mock_settings)
    
    client = ApifyScraperClient()
    
    run_response = mocker.Mock()
    run_response.is_success = True
    run_response.json.return_value = {"data": {"id": "test_run_id"}}
    
    failed_response = mocker.Mock()
    failed_response.is_success = True
    failed_response.json.return_value = {"data": {"status": "FAILED"}}
    
    mock_client.post.side_effect = [run_response]
    mock_client.get.side_effect = [failed_response]
    
    with pytest.raises(ApifyJobError):
        await client.scrape_skus("test_site", ["12345"])


@pytest.mark.asyncio
async def test_scrape_skus_auth_failure(mocker):
    mock_client = mocker.AsyncMock()
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    mock_settings = mocker.Mock()
    mock_settings.get.side_effect = lambda key: {
        'apify_api_token': 'test_token',
        'apify_base_url': 'https://api.apify.com/v2'
    }.get(key)
    mocker.patch('src.core.scrapers.apify_client.SettingsManager', return_value=mock_settings)
    
    client = ApifyScraperClient()
    
    auth_fail_response = mocker.Mock()
    auth_fail_response.is_success = False
    auth_fail_response.status_code = 401
    auth_fail_response.text = "Unauthorized"
    
    mock_client.post.side_effect = [auth_fail_response]
    
    with pytest.raises(ApifyAuthError):
        await client.scrape_skus("test_site", ["12345"])


@pytest.mark.asyncio
async def test_get_job_status(mocker):
    mock_client = mocker.AsyncMock()
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    mock_settings = mocker.Mock()
    mock_settings.get.side_effect = lambda key: {
        'apify_api_token': 'test_token',
        'apify_base_url': 'https://api.apify.com/v2'
    }.get(key)
    mocker.patch('src.core.scrapers.apify_client.SettingsManager', return_value=mock_settings)
    
    client = ApifyScraperClient()
    
    status_response = mocker.Mock()
    status_response.is_success = True
    status_response.json.return_value = {"data": {"status": "SUCCEEDED", "id": "test_job"}}
    
    mock_client.get.side_effect = [status_response]
    
    result = await client.get_job_status("test_job_id")
    assert result == {"data": {"status": "SUCCEEDED", "id": "test_job"}}


@pytest.mark.asyncio
async def test_cancel_job(mocker):
    mock_client = mocker.AsyncMock()
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    mock_settings = mocker.Mock()
    mock_settings.get.side_effect = lambda key: {
        'apify_api_token': 'test_token',
        'apify_base_url': 'https://api.apify.com/v2'
    }.get(key)
    mocker.patch('src.core.scrapers.apify_client.SettingsManager', return_value=mock_settings)
    
    client = ApifyScraperClient()
    
    abort_response = mocker.Mock()
    abort_response.is_success = True
    abort_response.json.return_value = {"data": {"status": "ABORTING"}}
    
    mock_client.post.side_effect = [abort_response]
    
    result = await client.cancel_job("test_job_id")
    assert result is True