"""
Device Recommender Utility

This module provides utilities for recommending Bitwig devices based on
natural language descriptions of audio tasks.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from bitwig_mcp_server.utils.browser_indexer import BitwigBrowserIndexer

# Setup logging
logger = logging.getLogger(__name__)


class BitwigDeviceRecommender:
    """Recommends Bitwig devices based on natural language descriptions."""

    def __init__(self, persistent_dir: str = None):
        """Initialize the device recommender.

        Args:
            persistent_dir: Directory where the ChromaDB data is stored
        """
        if persistent_dir is None:
            # Use the data directory in the project by default
            persistent_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "browser_index",
            )

        self.indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

        # Check if the index exists
        if self.indexer.get_device_count() == 0:
            logger.warning(
                f"No index found in {persistent_dir}. Recommendations may not work."
            )

    def recommend_devices(
        self,
        task_description: str,
        num_results: int = 5,
        filter_category: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Recommend devices based on a task description.

        Args:
            task_description: Natural language description of the audio task
            num_results: Number of results to return
            filter_category: Optional category filter
            filter_type: Optional type filter

        Returns:
            List of recommended devices with explanations
        """
        # Check if we have an index first
        if self.indexer.get_device_count() == 0:
            logger.warning(
                "No devices in the index. Please run the indexer first: python -m bitwig_mcp_server.utils.index_browser index"
            )
            return []

        # Prepare filter options
        filter_options = {}
        if filter_category:
            filter_options["category"] = filter_category
        if filter_type:
            filter_options["type"] = filter_type

        # Use None if no filters were specified
        if not filter_options:
            filter_options = None

        try:
            # Search for devices matching the task description
            search_results = self.indexer.search_devices(
                query=task_description,
                n_results=num_results,
                filter_options=filter_options,
            )

            # Enhance results with explanations
            recommendations = []
            for result in search_results:
                # Extract reasons why this device is a good match
                reasons = self._generate_explanation(task_description, result)

                # Add to recommendations
                recommendations.append(
                    {
                        "device": result["name"],
                        "category": result["category"],
                        "type": result["type"],
                        "creator": result["creator"],
                        "description": result["description"],
                        "tags": result["tags"],
                        "explanation": reasons,
                        "relevance_score": 1.0
                        - (
                            result["distance"]
                            if result.get("distance") is not None
                            else 0
                        ),
                    }
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error recommending devices: {e}")
            return []

    def _generate_explanation(
        self, task_description: str, device_info: Dict[str, Any]
    ) -> str:
        """Generate an explanation of why a device is recommended for a task.

        Args:
            task_description: Description of the audio task
            device_info: Information about the device

        Returns:
            Explanation text
        """
        # Extract keywords from the task description
        task_keywords = self._extract_keywords(task_description.lower())

        # Extract device information
        device_name = device_info["name"]
        device_category = device_info["category"]
        device_type = device_info["type"]
        device_description = device_info.get("description", "")
        device_tags = device_info.get("tags", [])

        # Compile all device text for matching
        device_text = f"{device_name} {device_category} {device_type} {device_description} {' '.join(device_tags)}".lower()
        device_keywords = self._extract_keywords(device_text)

        # Find matching keywords
        matching_keywords = task_keywords.intersection(device_keywords)

        # Generate explanation based on matches
        if matching_keywords:
            keyword_list = ", ".join(list(matching_keywords)[:5])  # Limit to 5 keywords
            explanation = f"This device matches your needs for: {keyword_list}"

            # Add category-specific explanations
            if device_category:
                explanation += f". It's a {device_category} device"

            # Add description-based explanation if available
            if device_description:
                # Just use the first sentence for brevity
                first_sentence = device_description.split(".")[0] + "."
                explanation += f". {first_sentence}"

            return explanation
        else:
            # Generic explanation when no specific matches are found
            return f"This {device_category} device may help with your task based on semantic similarity."

    def _extract_keywords(self, text: str) -> set:
        """Extract keyword set from text for matching.

        Args:
            text: Text to extract keywords from

        Returns:
            Set of extracted keywords
        """
        # Simple keyword extraction - split by spaces and punctuation
        import re

        words = re.findall(r"\b\w+\b", text.lower())

        # Filter out common words
        stopwords = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "if",
            "because",
            "as",
            "what",
            "when",
            "where",
            "how",
            "all",
            "any",
            "both",
            "each",
            "few",
            "more",
            "most",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "s",
            "t",
            "can",
            "will",
            "just",
            "don",
            "should",
            "now",
            "to",
            "of",
            "for",
            "with",
            "in",
            "on",
            "at",
            "by",
            "from",
            "up",
            "about",
            "into",
            "over",
            "after",
        }

        # Filter out short words and stopwords
        keywords = {word for word in words if len(word) > 2 and word not in stopwords}

        # Add audio-specific terms that might be important even if they're short
        audio_terms = {"eq", "mix", "pan", "bus", "fx", "db", "mid", "low", "hi", "amp"}
        keywords.update({word for word in words if word in audio_terms})

        return keywords

    def get_available_filters(self) -> Dict[str, List[str]]:
        """Get available filter options for recommendations.

        Returns:
            Dictionary with available filter options (categories, types)
        """
        stats = self.indexer.get_collection_stats()
        return {
            "categories": stats.get("categories", []),
            "types": stats.get("types", []),
            "creators": stats.get("creators", []),
        }


# Example usage:
# recommender = BitwigDeviceRecommender()
# devices = recommender.recommend_devices("I want to make my bass sound fatter with distortion")
# for device in devices:
#     print(f"{device['device']} - {device['explanation']}")

# Filter example:
# devices = recommender.recommend_devices(
#     "I want to make my bass sound fatter",
#     filter_category="Distortion"
# )
