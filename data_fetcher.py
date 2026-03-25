#############################################################################
# data_fetcher.py
#
# This file contains functions to fetch data needed for the app.
#############################################################################

import random
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = 'susana-rojas-fiu'
DATASET = 'ISE'


def get_user_sensor_data(user_id, workout_id):
    """Returns a list of timestamped information for a given workout."""
    client = bigquery.Client(project=PROJECT_ID)

    # Query SensorData and JOIN SensorTypes to get sensor name and units
    query = f"""
        SELECT st.Name, st.Units, sd.Timestamp, sd.SensorValue
        FROM `{PROJECT_ID}.{DATASET}.SensorData` sd
        JOIN `{PROJECT_ID}.{DATASET}.SensorTypes` st ON sd.SensorId = st.SensorId
        WHERE sd.WorkoutID = @workout_id
        ORDER BY sd.Timestamp
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('workout_id', 'STRING', workout_id),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            'sensor_type': row.Name,
            'timestamp': str(row.Timestamp),
            'data': row.SensorValue,
            'units': row.Units,
        }
        for row in rows
    ]


def get_user_workouts(user_id):
    """Returns a list of user's workouts."""
    client = bigquery.Client(project=PROJECT_ID)

    # Query Workouts table for all workouts belonging to the given user
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET}.Workouts`
        WHERE UserId = @user_id
        ORDER BY StartTimestamp DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            'workout_id': row.WorkoutId,
            'start_timestamp': str(row.StartTimestamp),
            'end_timestamp': str(row.EndTimestamp),
            'start_lat_lng': (row.StartLocationLat, row.StartLocationLong),
            'end_lat_lng': (row.EndLocationLat, row.EndLocationLong),
            'distance': row.TotalDistance,
            'steps': row.TotalSteps,
            'calories_burned': row.CaloriesBurned,
        }
        for row in rows
    ]


def get_user_profile(user_id):
    """Returns information about the given user."""
    client = bigquery.Client(project=PROJECT_ID)

    # Query Users table for the user's profile
    query = f"""
        SELECT Name, Username, DateOfBirth, ImageUrl
        FROM `{PROJECT_ID}.{DATASET}.Users`
        WHERE UserId = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        raise ValueError(f'User {user_id} not found.')
    user = rows[0]

    # Query Friends table checking both directions of friendship
    friends_query = f"""
        SELECT
            CASE WHEN UserId1 = @user_id THEN UserId2 ELSE UserId1 END AS FriendId
        FROM `{PROJECT_ID}.{DATASET}.Friends`
        WHERE UserId1 = @user_id OR UserId2 = @user_id
    """
    friends_rows = client.query(friends_query, job_config=job_config).result()
    friends = [row.FriendId for row in friends_rows]

    return {
        'full_name': user.Name,
        'username': user.Username,
        'date_of_birth': str(user.DateOfBirth),
        'profile_image': user.ImageUrl,
        'friends': friends,
    }


def get_user_posts(user_id):
    """Returns a list of a user's posts."""
    client = bigquery.Client(project=PROJECT_ID)

    # Query Posts table for all posts belonging to the given user
    query = f"""
        SELECT PostId, AuthorId, Timestamp, ImageUrl, Content
        FROM `{PROJECT_ID}.{DATASET}.Posts`
        WHERE AuthorId = @user_id
        ORDER BY Timestamp DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
        ]
    )
    rows = client.query(query, job_config=job_config).result()
    return [
        {
            'user_id': row.AuthorId,
            'post_id': row.PostId,
            'timestamp': str(row.Timestamp),
            'content': row.Content,
            'image': row.ImageUrl,
        }
        for row in rows
    ]


def get_genai_advice(user_id):
    """Returns advice from Vertex AI based on the user's workout data."""
    client = bigquery.Client(project=PROJECT_ID)
    workouts = get_user_workouts(user_id)
    profile = get_user_profile(user_id)

    workout_summary = ''
    if workouts:
        latest = workouts[0]
        workout_summary = (
            f"Latest workout: {latest['steps']} steps, "
            f"{latest['distance']} km, "
            f"{latest['calories_burned']} calories burned."
        )

    prompt = (
        f"You are a fitness coach. Give one short encouraging tip (2-3 sentences) "
        f"to {profile['full_name']} based on their recent activity. {workout_summary}"
    )

    vertexai.init(project=PROJECT_ID, location='us-central1')
    model = GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content(prompt)
    advice_text = response.text

    image = random.choice([
        'https://plus.unsplash.com/premium_photo-1669048780129-051d670fa2d1?q=80&w=3870&auto=format&fit=crop',
        None,
    ])

    return {
        'advice_id': 'advice1',
        'timestamp': str(__import__('datetime').datetime.now()),
        'content': advice_text,
        'image': image,
    }