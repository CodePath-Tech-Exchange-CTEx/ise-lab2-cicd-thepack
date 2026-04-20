#############################################################################
# data_fetcher.py
#
# This file contains functions to fetch data needed for the app.
#############################################################################

import random
import uuid
import streamlit as st
from datetime import datetime
from google.cloud import bigquery, storage
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = 'susana-rojas-fiu'
DATASET = 'ISE'
GCS_BUCKET = 'susana-rojas-fiu-media'


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
def get_user_posts(user_id):
    """Returns a list of a user's posts."""
    client = bigquery.Client(project=PROJECT_ID)

    # Query Posts table for all posts belonging to the given user
    query = f"""
        SELECT PostId, AuthorId, Timestamp, ImageUrl, Content
        FROM `{PROJECT_ID}.{DATASET}.Posts`
        WHERE AuthorId = @user_id
        QUALIFY ROW_NUMBER() OVER (PARTITION BY PostId ORDER BY Timestamp) = 1
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


@st.cache_data(ttl=600)
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


FREE_EXERCISE_DB_URL = 'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json'
FREE_EXERCISE_IMG_BASE = 'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises'

FOCUS_TO_MUSCLES = {
    'Chest': ['chest'],
    'Back': ['lats', 'middle back', 'lower back', 'traps'],
    'Legs': ['quadriceps', 'hamstrings', 'glutes', 'calves'],
    'Shoulders': ['shoulders', 'traps'],
    'Arms': ['biceps', 'triceps', 'forearms'],
    'Core': ['abdominals'],
}


@st.cache_data(ttl=86400)
def get_all_exercises():
    """Fetches the full exercise list from the free-exercise-db on GitHub."""
    import requests
    resp = requests.get(FREE_EXERCISE_DB_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=3600)
def get_workout_plan(user_id, focus):
    """Filters exercises by muscle group, asks Gemini to build a structured plan,
    then returns the selected exercises with image URLs."""
    import json

    all_exercises = get_all_exercises()
    target_muscles = FOCUS_TO_MUSCLES.get(focus, [focus.lower()])

    # Filter to exercises that target the right muscles and have images
    candidates = [
        ex for ex in all_exercises
        if any(m in ex.get('primaryMuscles', []) for m in target_muscles)
        and ex.get('images')
    ]

    # Build compact list for Gemini
    exercise_list = [
        {
            'id': ex['id'],
            'name': ex['name'],
            'primaryMuscles': ex['primaryMuscles'],
            'equipment': ex.get('equipment', 'body only'),
            'level': ex.get('level', 'intermediate'),
        }
        for ex in candidates
    ]

    profile = get_user_profile(user_id)

    prompt = (
        f"You are a personal trainer building a {focus} day workout for {profile['full_name']}. "
        f"Choose 5 to 6 exercises from this list that form a balanced, effective workout. "
        f"Vary the equipment and muscle emphasis where possible. "
        f"Return ONLY a valid JSON array. Each item must have these exact keys: "
        f"\"id\" (exercise id from the list), "
        f"\"sets\" (integer), "
        f"\"reps\" (string e.g. \"8-12\" or \"15\"), "
        f"\"tip\" (one short form cue, max 15 words). "
        f"No markdown, no explanation, just the JSON array.\n\n"
        f"Exercise list:\n{json.dumps(exercise_list)}"
    )

    vertexai.init(project=PROJECT_ID, location='us-central1')
    model = GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content(prompt)

    raw = response.text.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    selected = json.loads(raw)

    exercise_map = {ex['id']: ex for ex in candidates}
    plan = []
    for item in selected:
        ex = exercise_map.get(item['id'])
        if not ex:
            continue
        plan.append({
            'name': ex['name'],
            'primaryMuscles': ex.get('primaryMuscles', []),
            'secondaryMuscles': ex.get('secondaryMuscles', []),
            'equipment': ex.get('equipment', 'body only'),
            'level': ex.get('level', ''),
            'mechanic': ex.get('mechanic', ''),
            'instructions': ex.get('instructions', []),
            'imageUrl': f"{FREE_EXERCISE_IMG_BASE}/{ex['images'][0]}",
            'sets': item['sets'],
            'reps': item['reps'],
            'tip': item['tip'],
        })

    return plan


def upload_image_to_gcs(file_bytes, filename, content_type='image/jpeg'):
    """Uploads an image to GCS and returns its public URL."""
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(f'posts/{uuid.uuid4()}_{filename}')
    blob.upload_from_string(file_bytes, content_type=content_type)
    return f'https://storage.googleapis.com/{GCS_BUCKET}/{blob.name}'


def delete_post(post_id, user_id):
    """Deletes a post from the Posts table. Only deletes if the post belongs to the user."""
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        DELETE FROM `{PROJECT_ID}.{DATASET}.Posts`
        WHERE PostId = @post_id AND AuthorId = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('post_id', 'STRING', post_id),
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
        ]
    )
    client.query(query, job_config=job_config).result()
    get_user_posts.clear()


def create_post(user_id, content, image_url=None):
    """Inserts a new post into the Posts table."""
    client = bigquery.Client(project=PROJECT_ID)
    post_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET}.Posts` (PostId, AuthorId, Timestamp, ImageUrl, Content)
        VALUES (@post_id, @user_id, @timestamp, @image_url, @content)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter('post_id', 'STRING', post_id),
            bigquery.ScalarQueryParameter('user_id', 'STRING', user_id),
            bigquery.ScalarQueryParameter('timestamp', 'DATETIME', timestamp),
            bigquery.ScalarQueryParameter('image_url', 'STRING', image_url),
            bigquery.ScalarQueryParameter('content', 'STRING', content),
        ]
    )
    client.query(query, job_config=job_config).result()
    get_user_posts.clear()