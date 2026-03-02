#############################################################################
# modules_test.py
#
# This file contains tests for modules.py.
#
# You will write these tests in Unit 2.
#############################################################################

import unittest
from streamlit.testing.v1 import AppTest
from modules import display_post, display_activity_summary, display_genai_advice, display_recent_workouts

class TestDisplayPost(unittest.TestCase):
    """Tests the display_post function."""

    def test_display_post(self):
        """Tests that display_post runs without error."""
        at = AppTest.from_function(
            lambda: display_post(
                username='testuser',
                user_image=None,
                timestamp='2024-01-01 00:00:00',
                content='Hello world!',
                post_image=None,
            )
        )
        at.run()
        self.assertFalse(at.exception)


class TestDisplayActivitySummary(unittest.TestCase):
    """Tests the display_activity_summary function."""

    def test_display_activity_summary(self):
        """Tests that display_activity_summary runs without error."""
        workouts = [{
            'start_timestamp': '2024-01-01 00:00:00',
            'end_timestamp': '2024-01-01 00:30:00',
            'distance': 3.5,
            'steps': 5000,
            'calories_burned': 300,
            'start_lat_lng': (1.0, 4.0),
            'end_lat_lng': (1.1, 4.1),
        }]
        at = AppTest.from_function(lambda: display_activity_summary(workouts))
        at.run()
        self.assertFalse(at.exception)


class TestDisplayRecentWorkouts(unittest.TestCase):
    """Tests the display_recent_workouts function."""

    def test_display_recent_workouts(self):
        """Tests that display_recent_workouts runs without error."""
        workouts = [{
            'start_timestamp': '2024-01-01 00:00:00',
            'end_timestamp': '2024-01-01 00:30:00',
            'distance': 5.0,
            'steps': 8000,
            'calories_burned': 400,
            'start_lat_lng': (1.0, 4.0),
            'end_lat_lng': (1.1, 4.1),
        }]
        at = AppTest.from_function(lambda: display_recent_workouts(workouts))
        at.run()
        self.assertFalse(at.exception)


class TestDisplayGenAiAdvice(unittest.TestCase):
    """Tests the display_genai_advice function."""

    def test_display_genai_advice(self):
        """Tests that display_genai_advice runs without error."""
        at = AppTest.from_function(
            lambda: display_genai_advice(
                timestamp='2024-01-01 00:00:00',
                content='Keep up the good work!',
                image=None,
            )
        )
        at.run()
        self.assertFalse(at.exception)


if __name__ == "__main__":
    unittest.main()
