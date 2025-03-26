"""Tests for the device_recommender module"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from bitwig_mcp_server.utils.device_recommender import BitwigDeviceRecommender


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for test index"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_indexer():
    """Create a mock indexer for testing"""
    mock_indexer = MagicMock()

    # Mock search_devices method
    mock_search_results = [
        {
            "id": "device_1",
            "name": "Polysynth",
            "type": "Instrument",
            "category": "Synthesizer",
            "creator": "Bitwig",
            "tags": ["analog", "polyphonic"],
            "description": "A polyphonic synthesizer with analog character",
            "document": "Name: Polysynth. Type: Instrument. Category: Synthesizer. Creator: Bitwig. Tags: analog, polyphonic.",
            "distance": 0.1,
        },
        {
            "id": "device_2",
            "name": "FM-4",
            "type": "Instrument",
            "category": "Synthesizer",
            "creator": "Bitwig",
            "tags": ["fm", "digital"],
            "description": "An FM synthesizer with modern digital sound",
            "document": "Name: FM-4. Type: Instrument. Category: Synthesizer. Creator: Bitwig. Tags: fm, digital.",
            "distance": 0.2,
        },
        {
            "id": "device_3",
            "name": "Delay+",
            "type": "Effect",
            "category": "Delay",
            "creator": "Bitwig",
            "tags": ["time-based", "stereo"],
            "description": "A delay effect with advanced modulation options",
            "document": "Name: Delay+. Type: Effect. Category: Delay. Creator: Bitwig. Tags: time-based, stereo.",
            "distance": 0.3,
        },
    ]
    mock_indexer.search_devices.return_value = mock_search_results

    # Mock get_collection_stats method
    mock_indexer.get_collection_stats.return_value = {
        "count": 3,
        "categories": ["Synthesizer", "Delay", "Reverb"],
        "types": ["Instrument", "Effect"],
        "creators": ["Bitwig", "Third Party"],
    }

    # Mock get_device_count method
    mock_indexer.get_device_count.return_value = 3

    return mock_indexer


def test_recommender_init(temp_index_dir):
    """Test initializing BitwigDeviceRecommender"""
    with patch(
        "bitwig_mcp_server.utils.device_recommender.BitwigBrowserIndexer"
    ) as mock_indexer_class:
        # Create recommender
        recommender = BitwigDeviceRecommender(persistent_dir=temp_index_dir)

        # Check that BitwigBrowserIndexer was initialized with the right directory
        mock_indexer_class.assert_called_once_with(persistent_dir=temp_index_dir)
        assert recommender.indexer == mock_indexer_class.return_value


def test_recommend_devices(temp_index_dir, mock_indexer):
    """Test recommending devices"""
    # Create recommender with mock indexer
    recommender = BitwigDeviceRecommender(persistent_dir=temp_index_dir)
    recommender.indexer = mock_indexer

    # Test with basic parameters
    results = recommender.recommend_devices("analog synth with warm pads")

    # Check that search_devices was called correctly
    mock_indexer.search_devices.assert_called_once_with(
        query="analog synth with warm pads", n_results=5, filter_options=None
    )

    # Check results structure
    assert len(results) == 3
    assert results[0]["device"] == "Polysynth"
    assert results[0]["category"] == "Synthesizer"
    assert results[0]["type"] == "Instrument"
    assert results[0]["creator"] == "Bitwig"
    assert "explanation" in results[0]
    assert results[0]["relevance_score"] == 0.9  # 1.0 - 0.1

    # Test with category filter
    mock_indexer.search_devices.reset_mock()
    results = recommender.recommend_devices(
        "analog synth", filter_category="Synthesizer", num_results=2
    )

    # Check that search_devices was called with correct filters
    mock_indexer.search_devices.assert_called_once_with(
        query="analog synth", n_results=2, filter_options={"category": "Synthesizer"}
    )

    # Test with type filter
    mock_indexer.search_devices.reset_mock()
    results = recommender.recommend_devices(
        "echo with modulation", filter_type="Effect", num_results=1
    )

    # Check that search_devices was called with correct filters
    mock_indexer.search_devices.assert_called_once_with(
        query="echo with modulation", n_results=1, filter_options={"type": "Effect"}
    )

    # Test with both filters
    mock_indexer.search_devices.reset_mock()
    results = recommender.recommend_devices(
        "synth", filter_category="Synthesizer", filter_type="Instrument"
    )

    # Check that search_devices was called with correct filters
    call_kwargs = mock_indexer.search_devices.call_args[1]
    assert call_kwargs["filter_options"] == {
        "category": "Synthesizer",
        "type": "Instrument",
    }


def test_generate_explanation():
    """Test generating explanations for recommendations"""
    recommender = BitwigDeviceRecommender()

    # Test with matching keywords
    device_info = {
        "name": "Polysynth",
        "type": "Instrument",
        "category": "Synthesizer",
        "creator": "Bitwig",
        "tags": ["analog", "polyphonic"],
        "description": "A polyphonic synthesizer with analog character",
    }

    explanation = recommender._generate_explanation(
        "I want an analog synth for warm pads", device_info
    )

    # Check that explanation mentions the matching keywords
    assert "analog" in explanation.lower()
    assert "synth" in explanation.lower()
    assert "Synthesizer" in explanation

    # Test without matching keywords
    explanation = recommender._generate_explanation(
        "I need some interesting percussion", device_info
    )

    # Check that a generic explanation is provided
    assert "Synthesizer device" in explanation
    assert "may help" in explanation


def test_extract_keywords():
    """Test keyword extraction"""
    recommender = BitwigDeviceRecommender()

    # Test with simple phrase
    keywords = recommender._extract_keywords("analog synth with warm pads")
    assert "analog" in keywords
    assert "synth" in keywords
    assert "warm" in keywords
    assert "pads" in keywords
    assert "with" not in keywords  # Common words should be filtered

    # Test with audio-specific terms that might be short
    keywords = recommender._extract_keywords("eq with low mid adjustment")
    assert "eq" in keywords  # Should keep audio terms even if short
    assert "low" in keywords
    assert "mid" in keywords
    assert "adjustment" in keywords


def test_get_available_filters(mock_indexer):
    """Test getting available filter options"""
    # Create recommender with mock indexer
    recommender = BitwigDeviceRecommender()
    recommender.indexer = mock_indexer

    # Get available filters
    filters = recommender.get_available_filters()

    # Check results
    assert "categories" in filters
    assert "Synthesizer" in filters["categories"]
    assert "Delay" in filters["categories"]
    assert "types" in filters
    assert "Instrument" in filters["types"]
    assert "Effect" in filters["types"]
    assert "creators" in filters
    assert "Bitwig" in filters["creators"]

    # Ensure the indexer method was called
    mock_indexer.get_collection_stats.assert_called_once()


def test_empty_index_handling():
    """Test handling when index is empty"""
    # Create a mock indexer that reports empty index
    mock_indexer = MagicMock()
    mock_indexer.get_device_count.return_value = 0

    # Create recommender with mock indexer
    recommender = BitwigDeviceRecommender()
    recommender.indexer = mock_indexer

    # Try to get recommendations
    results = recommender.recommend_devices("synth")

    # Check that an empty list is returned
    assert results == []

    # Ensure search_devices wasn't called
    mock_indexer.search_devices.assert_not_called()
