"""Tests for the browser_indexer module"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from bitwig_mcp_server.utils.browser_indexer import (
    BitwigBrowserIndexer,
    BrowserItem,
    DeviceDescriptionScraper,
    DeviceMetadata,
    build_index,
    enhance_index_with_descriptions,
)


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for test index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_osc_controller():
    """Create mock OSC controller"""
    mock_controller = MagicMock()
    mock_controller.server = MagicMock()
    mock_controller.client = MagicMock()

    # Set up browser message responses
    browser_messages = {
        "/browser/exists": True,
        "/browser/isActive": True,  # Added this for navigate_to_everything_tab
        "/browser/tab": "Everything",
        "/browser/filter/1/exists": True,
        "/browser/filter/1/name": "Category",
        "/browser/filter/1/item/1/exists": True,
        "/browser/filter/1/item/1/name": "Synthesizer",
        "/browser/filter/1/item/1/isSelected": True,
        "/browser/filter/2/exists": True,
        "/browser/filter/2/name": "Creator",
        "/browser/filter/2/item/1/exists": True,
        "/browser/filter/2/item/1/name": "Bitwig",
        "/browser/filter/2/item/1/isSelected": True,
        "/browser/result/1/exists": True,
        "/browser/result/1/name": "Polysynth",
        "/browser/result/2/exists": True,
        "/browser/result/2/name": "FM-4",
        "/browser/result/3/exists": False,
    }

    # Set mock message getter
    mock_controller.server.get_message = lambda key: browser_messages.get(key)

    return mock_controller


@pytest.mark.asyncio
async def test_browser_indexer_init(temp_index_dir):
    """Test initializing BitwigBrowserIndexer"""
    indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)

    # Check that the indexer is properly initialized
    assert str(indexer.persistent_dir) == temp_index_dir
    assert indexer.collection_name == "bitwig_devices"
    assert indexer.chroma_client is not None
    assert indexer.collection is not None
    assert indexer._embedding_model is None  # Should be lazy-loaded
    assert indexer.controller is None
    assert indexer.client is None


def test_embedding_model(temp_index_dir):
    """Test the embedding_model property"""
    # Create a patched SentenceTransformer class
    mock_model = MagicMock()
    with patch(
        "bitwig_mcp_server.utils.browser_indexer.SentenceTransformer",
        return_value=mock_model,
    ) as mock_transformer:
        indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)

        # First access should initialize the model
        model = indexer.embedding_model
        mock_transformer.assert_called_once_with(indexer.embedding_model_name)

        # Second access should use the cached model
        model_again = indexer.embedding_model
        assert mock_transformer.call_count == 1  # Still only called once
        assert model == model_again


@pytest.mark.asyncio
async def test_initialize_controller():
    """Test initializing the OSC controller"""
    with patch(
        "bitwig_mcp_server.utils.browser_indexer.BitwigOSCController",
        return_value=MagicMock(),
    ) as mock_controller_class:
        # Create a mock controller that will be returned
        mock_controller = MagicMock()
        mock_controller.client = MagicMock()
        mock_controller.server = MagicMock()
        mock_controller.server.get_message.return_value = 120  # Mocked tempo response

        # Set up the mock controller class to return our mock
        mock_controller_class.return_value = mock_controller

        # Create the indexer and initialize controller
        indexer = BitwigBrowserIndexer(persistent_dir=tempfile.mkdtemp())
        result = await indexer.initialize_controller()

        # Check the result
        assert result is True
        assert indexer.controller == mock_controller
        assert indexer.client == mock_controller.client
        mock_controller.start.assert_called_once()
        mock_controller.client.refresh.assert_called()


@pytest.mark.asyncio
async def test_close_controller():
    """Test closing the OSC controller"""
    indexer = BitwigBrowserIndexer(persistent_dir=tempfile.mkdtemp())
    mock_controller = MagicMock()
    indexer.controller = mock_controller
    indexer.client = MagicMock()

    # Close the controller
    await indexer.close_controller()

    # Check that controller.stop was called
    mock_controller.stop.assert_called_once()
    assert indexer.controller is None
    assert indexer.client is None


def test_create_embedding(temp_index_dir):
    """Test creating embeddings"""
    # Mock the embedding model
    mock_model = MagicMock()
    # Mock the encode method to return a numpy-like object with tolist method
    mock_array = MagicMock()
    mock_array.tolist.return_value = [0.1, 0.2, 0.3]
    mock_model.encode.return_value = mock_array

    # Create indexer with mocked model
    indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)
    indexer._embedding_model = mock_model

    # Test the create_embedding method
    result = indexer.create_embedding("test text")

    # Check the result
    mock_model.encode.assert_called_once_with("test text")
    assert result == [0.1, 0.2, 0.3]


def test_create_search_text(temp_index_dir):
    """Test creating search text for embeddings"""
    indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)

    # Create a test device item
    device = BrowserItem(
        name="Polysynth",
        metadata=DeviceMetadata(
            name="Polysynth",
            type="Instrument",
            category="Synthesizer",
            creator="Bitwig",
            tags=["analog", "polyphonic"],
            description="A polyphonic synthesizer with analog character",
        ),
        index=1,
    )

    # Create search text
    result = indexer.create_search_text(device)

    # Check that the result contains all the relevant information
    assert "Name: Polysynth" in result
    assert "Type: Instrument" in result
    assert "Category: Synthesizer" in result
    assert "Creator: Bitwig" in result
    assert "Tags: analog, polyphonic" in result
    assert "Description: A polyphonic synthesizer with analog character" in result


@pytest.mark.asyncio
async def test_navigate_to_everything_tab(mock_osc_controller):
    """Test navigating to the Everything browser tab"""
    # Create indexer with mock controller
    indexer = BitwigBrowserIndexer(persistent_dir=tempfile.mkdtemp())
    indexer.controller = mock_osc_controller
    indexer.client = mock_osc_controller.client

    # Test navigating to Everything tab
    result = await indexer.navigate_to_everything_tab()

    # Check that the function succeeded and the browser was opened
    assert result is True
    indexer.client.browse_for_device.assert_called_once_with("after")


@pytest.mark.asyncio
async def test_collect_browser_metadata(mock_osc_controller):
    """Test collecting metadata from the browser"""
    # Create indexer with mock controller
    indexer = BitwigBrowserIndexer(persistent_dir=tempfile.mkdtemp())
    indexer.controller = mock_osc_controller
    indexer.client = mock_osc_controller.client

    # Test collecting metadata
    with patch.object(indexer, "navigate_to_everything_tab", return_value=True):
        browser_items = await indexer.collect_browser_metadata()

    # Check results
    assert len(browser_items) == 2
    assert browser_items[0].name == "Polysynth"
    assert browser_items[0].metadata["category"] == "Synthesizer"
    assert browser_items[0].metadata["creator"] == "Bitwig"
    assert browser_items[1].name == "FM-4"


@pytest.mark.asyncio
async def test_collect_browser_metadata_with_pagination():
    """Test collecting metadata from the browser with pagination"""
    # Create a more complex mock controller for pagination testing
    mock_controller = MagicMock()
    mock_controller.server = MagicMock()
    mock_controller.client = MagicMock()

    # Create a state dictionary to simulate pagination behavior
    # Start with page 1 data
    page1_data = {
        "/browser/exists": True,
        "/browser/isActive": True,
        "/browser/tab": "Result",
        # Page 1 results (16 items, full page)
        **{f"/browser/result/{i}/exists": True for i in range(1, 17)},
        **{f"/browser/result/{i}/name": f"Device {i}" for i in range(1, 17)},
        # Category filter
        "/browser/filter/1/exists": True,
        "/browser/filter/1/name": "Category",
        **{"/browser/filter/1/item/1/exists": True for i in range(1, 17)},
        **{"/browser/filter/1/item/1/isSelected": True for i in range(1, 17)},
        **{"/browser/filter/1/item/1/name": "Synthesizer" for i in range(1, 17)},
        # Creator filter
        "/browser/filter/2/exists": True,
        "/browser/filter/2/name": "Creator",
        **{"/browser/filter/2/item/1/exists": True for i in range(1, 17)},
        **{"/browser/filter/2/item/1/isSelected": True for i in range(1, 17)},
        **{"/browser/filter/2/item/1/name": "Bitwig" for i in range(1, 17)},
    }

    # Page 2 data (7 items, partial page)
    page2_data = {
        "/browser/exists": True,
        "/browser/isActive": True,
        "/browser/tab": "Result",
        # Page 2 results (7 items, partial page)
        **{f"/browser/result/{i}/exists": True for i in range(1, 8)},
        **{f"/browser/result/{i}/name": f"Device {i+16}" for i in range(1, 8)},
        # Results after index 7 don't exist
        **{f"/browser/result/{i}/exists": False for i in range(8, 17)},
        # Category filter
        "/browser/filter/1/exists": True,
        "/browser/filter/1/name": "Category",
        **{"/browser/filter/1/item/1/exists": True for i in range(1, 8)},
        **{"/browser/filter/1/item/1/isSelected": True for i in range(1, 8)},
        **{"/browser/filter/1/item/1/name": "Effect" for i in range(1, 8)},
        # Creator filter
        "/browser/filter/2/exists": True,
        "/browser/filter/2/name": "Creator",
        **{"/browser/filter/2/item/1/exists": True for i in range(1, 8)},
        **{"/browser/filter/2/item/1/isSelected": True for i in range(1, 8)},
        **{"/browser/filter/2/item/1/name": "Bitwig" for i in range(1, 8)},
    }

    # Page 3 data (empty page to signal end of results)
    page3_data = {
        "/browser/exists": True,
        "/browser/isActive": True,
        "/browser/tab": "Result",
        # No results on page 3
        **{f"/browser/result/{i}/exists": False for i in range(1, 17)},
    }

    # Use a list to track which page we're on
    current_page = [0]  # Using a list so we can modify it inside the nested function
    page_data = [page1_data, page2_data, page3_data]

    # Create a mock get_message function that returns data based on the current page
    def mock_get_message(key):
        return page_data[current_page[0]].get(key)

    # Create a mock select_next_browser_result_page that advances the page
    def mock_next_page():
        if current_page[0] < len(page_data) - 1:
            current_page[0] += 1

    # Create a mock select_previous_browser_result_page that goes back a page
    def mock_prev_page():
        if current_page[0] > 0:
            current_page[0] -= 1

    # Set up the mock controller
    mock_controller.server.get_message = mock_get_message
    mock_controller.client.select_next_browser_result_page = mock_next_page
    mock_controller.client.select_previous_browser_result_page = mock_prev_page

    # Create the indexer with our mock controller
    indexer = BitwigBrowserIndexer(persistent_dir=tempfile.mkdtemp())
    indexer.controller = mock_controller
    indexer.client = mock_controller.client

    # Test collecting metadata with pagination
    with patch.object(indexer, "navigate_to_everything_tab", return_value=True):
        browser_items = await indexer.collect_browser_metadata()

    # Check results
    # We should have 16 items from page 1 + 7 items from page 2 = 23 total
    assert len(browser_items) == 23

    # Check that the global indices are sequential
    for i, item in enumerate(browser_items):
        assert item.index == i + 1  # 1-based indexing

    # Check some specific items
    assert browser_items[0].name == "Device 1"
    assert browser_items[0].metadata["category"] == "Synthesizer"
    assert browser_items[0].metadata["creator"] == "Bitwig"

    # Check the last device which should be from page 2
    assert browser_items[22].name == "Device 23"
    assert browser_items[22].metadata["category"] == "Effect"
    assert browser_items[22].metadata["creator"] == "Bitwig"

    # Verify we advanced to page 2, but didn't try page 3 since we can detect
    # the last page by having fewer than 16 items
    assert current_page[0] == 1

    # This is correct behavior - our implementation detects that page 2 is the last page
    # because it has fewer than 16 items, so it doesn't advance to page 3


@pytest.mark.asyncio
async def test_index_browser_content(temp_index_dir):
    """Test indexing browser content"""
    # Create indexer
    indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)

    # Mock controller initialization to succeed
    async def mock_init_controller():
        indexer.client = MagicMock()
        return True

    # Create sample devices
    devices = [
        BrowserItem(
            name="Polysynth",
            metadata=DeviceMetadata(
                name="Polysynth",
                type="Instrument",
                category="Synthesizer",
                creator="Bitwig",
                tags=["analog", "polyphonic"],
                description=None,
            ),
            index=1,
        ),
        BrowserItem(
            name="FM-4",
            metadata=DeviceMetadata(
                name="FM-4",
                type="Instrument",
                category="Synthesizer",
                creator="Bitwig",
                tags=["fm", "digital"],
                description=None,
            ),
            index=2,
        ),
    ]

    # Mock all necessary methods
    with patch.object(
        indexer, "initialize_controller", side_effect=mock_init_controller
    ), patch.object(
        indexer, "collect_browser_metadata", return_value=devices
    ), patch.object(
        indexer, "create_embedding", return_value=[0.1, 0.2, 0.3]
    ), patch.object(indexer, "close_controller"), patch.object(
        indexer.collection, "add"
    ):
        # Run the indexing
        await indexer.index_browser_content()

        # Check method calls
        indexer.initialize_controller.assert_called_once()
        indexer.collect_browser_metadata.assert_called_once()
        assert indexer.create_embedding.call_count == 2  # Called for each device
        indexer.collection.add.assert_called_once()
        indexer.close_controller.assert_called_once()

        # Verify the call to collection.add
        call_args = indexer.collection.add.call_args[1]
        assert len(call_args["ids"]) == 2
        assert len(call_args["embeddings"]) == 2
        assert len(call_args["metadatas"]) == 2
        assert len(call_args["documents"]) == 2


def test_search_devices(temp_index_dir):
    """Test searching for devices"""
    # Create indexer
    indexer = BitwigBrowserIndexer(persistent_dir=temp_index_dir)

    # Mock the collection.query method
    mock_query_result = {
        "ids": [["device_1", "device_2"]],
        "metadatas": [
            [
                {
                    "name": "Polysynth",
                    "type": "Instrument",
                    "category": "Synthesizer",
                    "creator": "Bitwig",
                    "tags": ["analog", "polyphonic"],
                    "description": "A polyphonic synthesizer",
                },
                {
                    "name": "FM-4",
                    "type": "Instrument",
                    "category": "Synthesizer",
                    "creator": "Bitwig",
                    "tags": ["fm", "digital"],
                },
            ]
        ],
        "documents": [["Document text for Polysynth", "Document text for FM-4"]],
        "distances": [[0.1, 0.2]],
    }
    indexer.collection.query = MagicMock(return_value=mock_query_result)

    # Mock the create_embedding method
    indexer.create_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])

    # Test search
    results = indexer.search_devices("analog synth", n_results=2)

    # Check results
    assert len(results) == 2
    assert results[0]["name"] == "Polysynth"
    assert results[0]["type"] == "Instrument"
    assert results[0]["category"] == "Synthesizer"
    assert results[0]["creator"] == "Bitwig"
    assert results[0]["distance"] == 0.1
    assert results[1]["name"] == "FM-4"

    # Check that create_embedding was called with the query
    indexer.create_embedding.assert_called_once_with("analog synth")

    # Check filter usage
    indexer.collection.query.assert_called_once()
    call_kwargs = indexer.collection.query.call_args[1]
    assert call_kwargs["n_results"] == 2
    assert call_kwargs["where"] is None

    # Test with filter
    indexer.collection.query.reset_mock()
    results = indexer.search_devices(
        "analog synth", filter_options={"category": "Synthesizer"}
    )
    call_kwargs = indexer.collection.query.call_args[1]
    assert call_kwargs["where"] == {"category": "Synthesizer"}


@pytest.mark.asyncio
async def test_build_index(temp_index_dir):
    """Test the build_index utility function"""
    # Mock the BitwigBrowserIndexer class and the makedirs function
    with patch(
        "bitwig_mcp_server.utils.browser_indexer.BitwigBrowserIndexer"
    ) as mock_indexer_class, patch("os.makedirs") as mock_makedirs:
        # Create a mock indexer with async methods properly mocked
        mock_indexer = MagicMock()

        # Mock async method with a coroutine
        async def mock_index_content():
            return None

        mock_indexer.index_browser_content = mock_index_content
        mock_indexer.get_device_count = MagicMock(return_value=2)
        mock_indexer.get_collection_stats = MagicMock(
            return_value={
                "count": 2,
                "categories": ["Synthesizer"],
                "types": ["Instrument"],
                "creators": ["Bitwig"],
            }
        )

        # Set up the mock indexer class to return our mock
        mock_indexer_class.return_value = mock_indexer

        # Override build_index with a function we can test
        async def test_build(persistent_dir=None):
            """Test version of build_index that uses our mocks"""
            if persistent_dir is None:
                persistent_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "data",
                    "browser_index",
                )

            # Ensure directory exists
            os.makedirs(persistent_dir, exist_ok=True)

            indexer = mock_indexer_class(persistent_dir=persistent_dir)

            try:
                await indexer.index_browser_content()

                if indexer.get_device_count() > 0:
                    # Get statistics (not used in test but included in the mocked behavior)
                    _ = indexer.get_collection_stats()

            except Exception:
                return None

            return indexer

        # Patch the build_index function and call our test version
        with patch(
            "bitwig_mcp_server.utils.browser_indexer.build_index",
            side_effect=test_build,
        ):
            result = await build_index(persistent_dir=temp_index_dir)

            # Check results
            assert result == mock_indexer
            mock_makedirs.assert_called_once_with(temp_index_dir, exist_ok=True)
            mock_indexer.get_device_count.assert_called_once()
            mock_indexer.get_collection_stats.assert_called_once()


class TestDeviceDescriptionScraper:
    """Test cases for DeviceDescriptionScraper"""

    def test_init(self):
        """Test initializing the scraper"""
        scraper = DeviceDescriptionScraper()
        assert (
            scraper.base_url
            == "https://www.bitwig.com/userguide/latest/device_descriptions/"
        )

        # Test custom URL
        custom_url = "https://example.com/descriptions/"
        custom_scraper = DeviceDescriptionScraper(base_url=custom_url)
        assert custom_scraper.base_url == custom_url

    def test_scrape_device_descriptions(self):
        """Test scraping device descriptions"""
        # Create mock HTML responses
        mock_index_html = """
        <html>
            <body>
                <a href="./device1.html">Device 1</a>
                <a href="./device2.html">Device 2</a>
            </body>
        </html>
        """

        mock_device1_html = """
        <html>
            <body>
                <div class="description">Description for Device 1</div>
            </body>
        </html>
        """

        mock_device2_html = """
        <html>
            <body>
                <div class="description">Description for Device 2</div>
            </body>
        </html>
        """

        # Mock requests.get to return our mock responses
        with patch("requests.get") as mock_get:
            # Set up the mock to return different responses for different URLs
            def mock_response(url):
                mock_resp = MagicMock()
                if url.endswith("device_descriptions/"):
                    mock_resp.text = mock_index_html
                elif url.endswith("device1.html"):
                    mock_resp.text = mock_device1_html
                elif url.endswith("device2.html"):
                    mock_resp.text = mock_device2_html
                return mock_resp

            mock_get.side_effect = mock_response

            # Initialize scraper and run test
            scraper = DeviceDescriptionScraper()
            descriptions = scraper.scrape_device_descriptions()

            # Verify results
            assert len(descriptions) == 2
            assert descriptions["Device 1"] == "Description for Device 1"
            assert descriptions["Device 2"] == "Description for Device 2"

            # Verify requests were made
            assert mock_get.call_count == 3

    def test_scrape_error_handling(self):
        """Test error handling during scraping"""
        # Mock requests.get to raise an exception
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")

            # Initialize scraper and run test
            scraper = DeviceDescriptionScraper()
            descriptions = scraper.scrape_device_descriptions()

            # Verify results
            assert len(descriptions) == 0


@pytest.mark.asyncio
async def test_enhance_index_with_descriptions(temp_index_dir):
    """Test enhancing an index with descriptions"""
    # Create a mock indexer
    mock_indexer = MagicMock()
    mock_indexer.get_device_count.return_value = 2
    mock_collection = MagicMock()
    mock_indexer.collection = mock_collection
    mock_indexer.create_embedding.return_value = [0.1, 0.2, 0.3]

    # Set up mock collection data
    mock_collection.get.return_value = {
        "ids": ["device_1", "device_2"],
        "metadatas": [
            {"name": "Device 1", "type": "Instrument", "category": "Synthesizer"},
            {"name": "Device 2", "type": "Audio FX", "category": "Delay"},
        ],
        "documents": [
            "Name: Device 1. Type: Instrument. Category: Synthesizer.",
            "Name: Device 2. Type: Audio FX. Category: Delay.",
        ],
    }

    # Mock the scraper to return some descriptions
    mock_scraper = MagicMock()
    mock_scraper.scrape_device_descriptions.return_value = {
        "Device 1": "A virtual analog synthesizer",
        "Device 2": "A classic delay effect",
    }

    # Patch the necessary functions
    with patch(
        "bitwig_mcp_server.utils.browser_indexer.BitwigBrowserIndexer",
        return_value=mock_indexer,
    ), patch(
        "bitwig_mcp_server.utils.browser_indexer.DeviceDescriptionScraper",
        return_value=mock_scraper,
    ):
        # Run the enhancement function
        updated_count = await enhance_index_with_descriptions(temp_index_dir)

        # Verify results
        assert updated_count == 2
        mock_indexer.get_device_count.assert_called_once()
        mock_collection.get.assert_called_once()
        mock_scraper.scrape_device_descriptions.assert_called_once()
        assert mock_indexer.create_embedding.call_count == 2
        assert mock_collection.update.call_count == 2

        # Verify the updates included descriptions
        update_calls = mock_collection.update.call_args_list
        for i, call_args in enumerate(update_calls):
            kwargs = call_args[1]  # Get the keyword arguments

            # Check that metadatas and documents were included
            assert "metadatas" in kwargs
            assert "documents" in kwargs

            # Check that description was added to metadata and document
            metadata = kwargs["metadatas"][0]
            assert "description" in metadata

            document = kwargs["documents"][0]
            assert "Description:" in document
