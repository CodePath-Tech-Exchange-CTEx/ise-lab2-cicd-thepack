#############################################################################
# data_fetcher.py
#
# This file contains functions to fetch data needed for the app.
#
# You will re-write these functions in Unit 3, and are welcome to alter the
# data returned in the meantime. We will replace this file with other data when
# testing earlier units.
#############################################################################

import random

# users = {
#     'user1': {
#         'full_name': 'Remi',
#         'username': 'remi_the_rems',
#         'date_of_birth': '1990-01-01',
#         'profile_image': 'https://upload.wikimedia.org/wikipedia/commons/c/c8/Puma_shoes.jpg',
#         'friends': ['user2', 'user3', 'user4'],
#     },
#     'user2': {
#         'full_name': 'Blake',
#         'username': 'blake',
#         'date_of_birth': '1990-01-01',
#         'profile_image': 'https://upload.wikimedia.org/wikipedia/commons/c/c8/Puma_shoes.jpg',
#         'friends': ['user1'],
#     },
#     'user3': {
#         'full_name': 'Jordan',
#         'username': 'jordanjordanjordan',
#         'date_of_birth': '1990-01-01',
#         'profile_image': 'https://upload.wikimedia.org/wikipedia/commons/c/c8/Puma_shoes.jpg',
#         'friends': ['user1', 'user4'],
#     },
#     'user4': {
#         'full_name': 'Gemmy',
#         'username': 'gems',
#         'date_of_birth': '1990-01-01',
#         'profile_image': 'https://upload.wikimedia.org/wikipedia/commons/c/c8/Puma_shoes.jpg',
#         'friends': ['user1', 'user3'],
#     },
# }


def get_user_sensor_data(user_id, workout_id):
    """Returns a list of timestampped information for a given workout.

    This function currently returns random data. You will re-write it in Unit 3.
    """
    from google.cloud import bigquery

    client = bigquery.Client()

    # Query SensorData and JOIN SensorTypes to get sensor name and units
    query = """
        SELECT st.Name as sensor_type, sd.Timestamp, sd.SensorValue as data, st.Units as units
        FROM `tesfaye-kefene-fisk.ISE.SensorData` sd
        JOIN `tesfaye-kefene-fisk.ISE.SensorTypes` st ON sd.SensorId = st.SensorId
        WHERE sd.WorkoutID = @workout_id
    """

    # Use parameterized query to safely pass workout_id
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("workout_id", "STRING", workout_id)]
    )

    results = client.query(query, job_config=job_config).result()

    # Build a list of sensor data dictionaries matching the required output format
    sensor_data = []
    for row in results:
        sensor_data.append({
            'sensor_type': row.sensor_type,
            'timestamp': str(row.Timestamp),
            'data': row.data,
            'units': row.units,
        })
    return sensor_data


def get_user_workouts(user_id):
    """Returns a list of user's workouts.

    This function currently returns random data. You will re-write it in Unit 3.
    """
    from google.cloud import bigquery

    client = bigquery.Client()

    # Query Workouts table for all workouts belonging to the given user
    query = """
        SELECT WorkoutId, StartTimestamp, EndTimestamp,
               StartLocationLat, StartLocationLong,
               EndLocationLat, EndLocationLong,
               TotalDistance, TotalSteps, CaloriesBurned
        FROM `tesfaye-kefene-fisk.ISE.Workouts`
        WHERE UserId = @user_id
    """

    # Use parameterized query to safely pass user_id
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )

    results = client.query(query, job_config=job_config).result()

    # Build a list of workout dictionaries matching the required output format
    workouts = []
    for row in results:
        workouts.append({
            'workout_id': row.WorkoutId,
            'start_timestamp': str(row.StartTimestamp),
            'end_timestamp': str(row.EndTimestamp),
            'start_lat_lng': (row.StartLocationLat, row.StartLocationLong),
            'end_lat_lng': (row.EndLocationLat, row.EndLocationLong),
            'distance': row.TotalDistance,
            'steps': row.TotalSteps,
            'calories_burned': row.CaloriesBurned,
        })
    return workouts


def get_user_profile(user_id):
    """Returns information about the given user.

    This function currently returns random data. You will re-write it in Unit 3.
    """
    from google.cloud import bigquery

    client = bigquery.Client()

    # Query Users table and LEFT JOIN Friends to get the user's friend list
    # LEFT JOIN ensures we still return the user even if they have no friends
    query = """
        SELECT u.Name, u.Username, u.ImageUrl, u.DateOfBirth,
               f.UserId2 as FriendId
        FROM `tesfaye-kefene-fisk.ISE.Users` u
        LEFT JOIN `tesfaye-kefene-fisk.ISE.Friends` f ON u.UserId = f.UserId1
        WHERE u.UserId = @user_id
    """

    # Use parameterized query to safely pass user_id
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )

    results = client.query(query, job_config=job_config).result()

    profile = None
    friends = []

    # Each row represents one friend, so we build the profile once
    # and collect all friend IDs across rows
    for row in results:
        if profile is None:
            profile = {
                'full_name': row.Name,
                'username': row.Username,
                'date_of_birth': str(row.DateOfBirth),
                'profile_image': row.ImageUrl,
                'friends': [],
            }
        if row.FriendId:
            friends.append(row.FriendId)

    # If no rows returned, the user does not exist
    if profile is None:
        raise ValueError(f'User {user_id} not found.')

    profile['friends'] = friends
    return profile


def get_user_posts(user_id):
    """Returns a list of a user's posts.

    This function currently returns random data. You will re-write it in Unit 3.
    """
    from google.cloud import bigquery

    client = bigquery.Client()

    # Query Posts table for all posts belonging to the given user
    query = """
        SELECT PostId, AuthorId, Timestamp, ImageUrl, Content
        FROM `tesfaye-kefene-fisk.ISE.Posts`
        WHERE AuthorId = @user_id
    """

    # Use parameterized query to safely pass user_id
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )

    results = client.query(query, job_config=job_config).result()

    # Build a list of post dictionaries matching the required output format
    posts = []
    for row in results:
        posts.append({
            'user_id': row.AuthorId,
            'post_id': row.PostId,
            'timestamp': str(row.Timestamp),
            'content': row.Content,
            'image': row.ImageUrl,
        })
    return posts



def get_genai_advice(user_id):
    """Returns the most recent advice from the genai model.

    This function currently returns random data. You will re-write it in Unit 3.
    """
    advice = random.choice([
        'Your heart rate indicates you can push yourself further. You got this!',
        "You're doing great! Keep up the good work.",
        'You worked hard yesterday, take it easy today.',
        'You have burned 100 calories so far today!',
    ])
    image = random.choice([
        'https://plus.unsplash.com/premium_photo-1669048780129-051d670fa2d1?q=80&w=3870&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
        None,
    ])
    return {
        'advice_id': 'advice1',
        'timestamp': '2024-01-01 00:00:00',
        'content': advice,
        'image': image,
    }
