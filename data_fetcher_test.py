#############################################################################
# data_fetcher_test.py
#
# This file contains tests for data_fetcher.py.
# BigQuery calls are mocked so tests run without GCP credentials.
#############################################################################

import unittest
from unittest.mock import patch, MagicMock
import data_fetcher


def make_row(**kwargs):
    row = MagicMock()
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row


class TestGetUserSensorData(unittest.TestCase):

    @patch('data_fetcher.bigquery.Client')
    def test_returns_list(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Heart Rate', Units='bpm', Timestamp='2024-07-29 07:15:00', SensorValue=120.0)
        ]
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        self.assertIsInstance(result, list)

    @patch('data_fetcher.bigquery.Client')
    def test_each_item_has_required_keys(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Heart Rate', Units='bpm', Timestamp='2024-07-29 07:15:00', SensorValue=120.0)
        ]
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        self.assertGreater(len(result), 0)
        for item in result:
            self.assertIn('sensor_type', item)
            self.assertIn('timestamp', item)
            self.assertIn('data', item)
            self.assertIn('units', item)

    @patch('data_fetcher.bigquery.Client')
    def test_data_is_numeric(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Heart Rate', Units='bpm', Timestamp='2024-07-29 07:15:00', SensorValue=120.0)
        ]
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        for item in result:
            self.assertIsInstance(item['data'], (int, float))

    @patch('data_fetcher.bigquery.Client')
    def test_timestamp_is_string(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Heart Rate', Units='bpm', Timestamp='2024-07-29 07:15:00', SensorValue=120.0)
        ]
        result = data_fetcher.get_user_sensor_data('user1', 'workout1')
        for item in result:
            self.assertIsInstance(item['timestamp'], str)


class TestGetUserWorkouts(unittest.TestCase):

    @patch('data_fetcher.bigquery.Client')
    def test_returns_list(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(WorkoutId='workout1', StartTimestamp='2024-07-29 07:00:00',
                     EndTimestamp='2024-07-29 08:00:00', StartLocationLat=37.77,
                     StartLocationLong=-122.41, EndLocationLat=37.80,
                     EndLocationLong=-122.42, TotalDistance=5.0, TotalSteps=8000,
                     CaloriesBurned=400.0)
        ]
        result = data_fetcher.get_user_workouts('user1')
        self.assertIsInstance(result, list)

    @patch('data_fetcher.bigquery.Client')
    def test_each_workout_has_required_keys(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(WorkoutId='workout1', StartTimestamp='2024-07-29 07:00:00',
                     EndTimestamp='2024-07-29 08:00:00', StartLocationLat=37.77,
                     StartLocationLong=-122.41, EndLocationLat=37.80,
                     EndLocationLong=-122.42, TotalDistance=5.0, TotalSteps=8000,
                     CaloriesBurned=400.0)
        ]
        result = data_fetcher.get_user_workouts('user1')
        self.assertGreater(len(result), 0)
        for key in ('workout_id', 'start_timestamp', 'end_timestamp',
                    'start_lat_lng', 'end_lat_lng', 'distance', 'steps', 'calories_burned'):
            self.assertIn(key, result[0])

    @patch('data_fetcher.bigquery.Client')
    def test_lat_lng_are_tuples(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(WorkoutId='workout1', StartTimestamp='2024-07-29 07:00:00',
                     EndTimestamp='2024-07-29 08:00:00', StartLocationLat=37.77,
                     StartLocationLong=-122.41, EndLocationLat=37.80,
                     EndLocationLong=-122.42, TotalDistance=5.0, TotalSteps=8000,
                     CaloriesBurned=400.0)
        ]
        result = data_fetcher.get_user_workouts('user1')
        self.assertIsInstance(result[0]['start_lat_lng'], tuple)
        self.assertIsInstance(result[0]['end_lat_lng'], tuple)

    @patch('data_fetcher.bigquery.Client')
    def test_steps_is_integer(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(WorkoutId='workout1', StartTimestamp='2024-07-29 07:00:00',
                     EndTimestamp='2024-07-29 08:00:00', StartLocationLat=37.77,
                     StartLocationLong=-122.41, EndLocationLat=37.80,
                     EndLocationLong=-122.42, TotalDistance=5.0, TotalSteps=8000,
                     CaloriesBurned=400.0)
        ]
        result = data_fetcher.get_user_workouts('user1')
        self.assertIsInstance(result[0]['steps'], int)


class TestGetUserProfile(unittest.TestCase):

    @patch('data_fetcher.bigquery.Client')
    def test_returns_dict(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Alice Johnson', Username='alicej',
                     DateOfBirth='1990-01-15', ImageUrl='http://example.com/alice.jpg')
        ]
        result = data_fetcher.get_user_profile('user1')
        self.assertIsInstance(result, dict)

    @patch('data_fetcher.bigquery.Client')
    def test_has_required_keys(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Alice Johnson', Username='alicej',
                     DateOfBirth='1990-01-15', ImageUrl='http://example.com/alice.jpg')
        ]
        result = data_fetcher.get_user_profile('user1')
        for key in ('full_name', 'username', 'date_of_birth', 'profile_image', 'friends'):
            self.assertIn(key, result)

    @patch('data_fetcher.bigquery.Client')
    def test_friends_is_list(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(Name='Alice Johnson', Username='alicej',
                     DateOfBirth='1990-01-15', ImageUrl='http://example.com/alice.jpg')
        ]
        result = data_fetcher.get_user_profile('user1')
        self.assertIsInstance(result['friends'], list)

    @patch('data_fetcher.bigquery.Client')
    def test_invalid_user_raises_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = []
        with self.assertRaises(Exception):
            data_fetcher.get_user_profile('nonexistent_user_xyz')


class TestGetUserPosts(unittest.TestCase):

    @patch('data_fetcher.bigquery.Client')
    def test_returns_list(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(PostId='post1', AuthorId='user1', Timestamp='2024-07-29 12:00:00',
                     ImageUrl='http://example.com/post1.jpg', Content='Great workout!')
        ]
        result = data_fetcher.get_user_posts('user1')
        self.assertIsInstance(result, list)

    @patch('data_fetcher.bigquery.Client')
    def test_each_post_has_required_keys(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(PostId='post1', AuthorId='user1', Timestamp='2024-07-29 12:00:00',
                     ImageUrl='http://example.com/post1.jpg', Content='Great workout!')
        ]
        result = data_fetcher.get_user_posts('user1')
        self.assertGreater(len(result), 0)
        for key in ('user_id', 'post_id', 'timestamp', 'content', 'image'):
            self.assertIn(key, result[0])

    @patch('data_fetcher.bigquery.Client')
    def test_user_id_matches_input(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(PostId='post1', AuthorId='user1', Timestamp='2024-07-29 12:00:00',
                     ImageUrl='http://example.com/post1.jpg', Content='Great workout!')
        ]
        result = data_fetcher.get_user_posts('user1')
        self.assertEqual(result[0]['user_id'], 'user1')

    @patch('data_fetcher.bigquery.Client')
    def test_content_is_string_or_none(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            make_row(PostId='post1', AuthorId='user1', Timestamp='2024-07-29 12:00:00',
                     ImageUrl='http://example.com/post1.jpg', Content='Great workout!')
        ]
        result = data_fetcher.get_user_posts('user1')
        for post in result:
            self.assertTrue(post['content'] is None or isinstance(post['content'], str))


class TestGetGenaiAdvice(unittest.TestCase):

    @patch('data_fetcher.get_user_workouts')
    @patch('data_fetcher.get_user_profile')
    def test_returns_dict(self, mock_profile, mock_workouts):
        mock_profile.return_value = {'full_name': 'Alice', 'username': 'alicej',
                                     'date_of_birth': '1990-01-15', 'profile_image': None, 'friends': []}
        mock_workouts.return_value = []
        with patch('vertexai.init'), \
             patch('vertexai.generative_models.GenerativeModel') as mock_model_class:
            mock_model_class.return_value.generate_content.return_value.text = 'Keep it up!'
            result = data_fetcher.get_genai_advice('user1')
        self.assertIsInstance(result, dict)

    @patch('data_fetcher.get_user_workouts')
    @patch('data_fetcher.get_user_profile')
    def test_has_required_keys(self, mock_profile, mock_workouts):
        mock_profile.return_value = {'full_name': 'Alice', 'username': 'alicej',
                                     'date_of_birth': '1990-01-15', 'profile_image': None, 'friends': []}
        mock_workouts.return_value = []
        with patch('vertexai.init'), \
             patch('vertexai.generative_models.GenerativeModel') as mock_model_class:
            mock_model_class.return_value.generate_content.return_value.text = 'Keep it up!'
            result = data_fetcher.get_genai_advice('user1')
        for key in ('advice_id', 'timestamp', 'content', 'image'):
            self.assertIn(key, result)

    @patch('data_fetcher.get_user_workouts')
    @patch('data_fetcher.get_user_profile')
    def test_content_is_nonempty_string(self, mock_profile, mock_workouts):
        mock_profile.return_value = {'full_name': 'Alice', 'username': 'alicej',
                                     'date_of_birth': '1990-01-15', 'profile_image': None, 'friends': []}
        mock_workouts.return_value = []
        with patch('vertexai.init'), \
             patch('vertexai.generative_models.GenerativeModel') as mock_model_class:
            mock_model_class.return_value.generate_content.return_value.text = 'Keep it up!'
            result = data_fetcher.get_genai_advice('user1')
        self.assertIsInstance(result['content'], str)
        self.assertGreater(len(result['content']), 0)

    @patch('data_fetcher.get_user_workouts')
    @patch('data_fetcher.get_user_profile')
    def test_image_is_none_or_string(self, mock_profile, mock_workouts):
        mock_profile.return_value = {'full_name': 'Alice', 'username': 'alicej',
                                     'date_of_birth': '1990-01-15', 'profile_image': None, 'friends': []}
        mock_workouts.return_value = []
        with patch('vertexai.init'), \
             patch('vertexai.generative_models.GenerativeModel') as mock_model_class:
            mock_model_class.return_value.generate_content.return_value.text = 'Keep it up!'
            result = data_fetcher.get_genai_advice('user1')
        self.assertTrue(result['image'] is None or isinstance(result['image'], str))

if __name__ == '__main__':
    unittest.main()