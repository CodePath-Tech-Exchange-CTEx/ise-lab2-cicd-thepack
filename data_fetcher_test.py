#############################################################################
# data_fetcher_test.py
#
# This file contains tests for data_fetcher.py.
#############################################################################

import unittest
import data_fetcher


class TestGetUserSensorData(unittest.TestCase):

    def test_returns_list(self):
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        self.assertIsInstance(result, list)  # Line written by Claude

    def test_each_item_has_required_keys(self):
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        self.assertGreater(len(result), 0)
        for item in result:
            self.assertIn('sensor_type', item)  # Line written by Claude
            self.assertIn('timestamp', item)  # Line written by Claude
            self.assertIn('data', item)  # Line written by Claude
            self.assertIn('units', item)  # Line written by Claude

    def test_data_is_numeric(self):
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        for item in result:
            self.assertIsInstance(item['data'], (int, float))  # Line written by Claude

    def test_timestamp_is_string(self):
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        for item in result:
            self.assertIsInstance(item['timestamp'], str)  # Line written by Claude


class TestGetUserWorkouts(unittest.TestCase):

    def test_returns_list(self):
        result = data_fetcher.get_user_workouts('user1')
        self.assertIsInstance(result, list)  # Line written by Claude

    def test_each_workout_has_required_keys(self):
        result = data_fetcher.get_user_workouts('user1')
        self.assertGreater(len(result), 0)
        required_keys = [
            'workout_id', 'start_timestamp', 'end_timestamp',
            'start_lat_lng', 'end_lat_lng', 'distance', 'steps', 'calories_burned'
        ]
        for workout in result:
            for key in required_keys:
                self.assertIn(key, workout)  # Line written by Claude

    def test_lat_lng_are_tuples(self):
        result = data_fetcher.get_user_workouts('user1')
        for workout in result:
            self.assertIsInstance(workout['start_lat_lng'], tuple)  # Line written by Claude
            self.assertIsInstance(workout['end_lat_lng'], tuple)  # Line written by Claude

    def test_steps_is_integer(self):
        result = data_fetcher.get_user_workouts('user1')
        for workout in result:
            self.assertIsInstance(workout['steps'], int)  # Line written by Claude


class TestGetUserProfile(unittest.TestCase):

    def test_returns_dict(self):
        result = data_fetcher.get_user_profile('user1')
        self.assertIsInstance(result, dict)  # Line written by Claude

    def test_has_required_keys(self):
        result = data_fetcher.get_user_profile('user1')
        for key in ('full_name', 'username', 'date_of_birth', 'profile_image', 'friends'):
            self.assertIn(key, result)  # Line written by Claude

    def test_friends_is_list(self):
        result = data_fetcher.get_user_profile('user1')
        self.assertIsInstance(result['friends'], list)  # Line written by Claude

    def test_invalid_user_raises_error(self):
        with self.assertRaises(Exception):  # Line written by Claude
            data_fetcher.get_user_profile('nonexistent_user_xyz')


class TestGetUserPosts(unittest.TestCase):

    def test_returns_list(self):
        result = data_fetcher.get_user_posts('user1')
        self.assertIsInstance(result, list)  # Line written by Claude

    def test_each_post_has_required_keys(self):
        result = data_fetcher.get_user_posts('user1')
        self.assertGreater(len(result), 0)
        for post in result:
            for key in ('user_id', 'post_id', 'timestamp', 'content', 'image'):
                self.assertIn(key, post)  # Line written by Claude

    def test_user_id_matches_input(self):
        result = data_fetcher.get_user_posts('user1')
        for post in result:
            self.assertEqual(post['user_id'], 'user1')  # Line written by Claude

    def test_content_is_string(self):
        result = data_fetcher.get_user_posts('user1')
        for post in result:
            self.assertIsInstance(post['content'], str)  # Line written by Claude
            self.assertGreater(len(post['content']), 0)  # Line written by Claude


class TestGetGenaiAdvice(unittest.TestCase):

    def test_returns_dict(self):
        result = data_fetcher.get_genai_advice('user1')
        self.assertIsInstance(result, dict)  # Line written by Claude

    def test_has_required_keys(self):
        result = data_fetcher.get_genai_advice('user1')
        for key in ('advice_id', 'timestamp', 'content', 'image'):
            self.assertIn(key, result)  # Line written by Claude

    def test_content_is_nonempty_string(self):
        result = data_fetcher.get_genai_advice('user1')
        self.assertIsInstance(result['content'], str)  # Line written by Claude
        self.assertGreater(len(result['content']), 0)  # Line written by Claude

    def test_image_is_none_or_string(self):
        result = data_fetcher.get_genai_advice('user1')
        self.assertTrue(
            result['image'] is None or isinstance(result['image'], str)
        )  # Line written by Claude


if __name__ == '__main__':
    unittest.main()
