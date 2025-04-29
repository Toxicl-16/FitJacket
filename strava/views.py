# strava/views.py

import os
import requests
from dotenv import load_dotenv
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StravaActivity
from dashboard.models import Goal

load_dotenv()

@login_required
def strava_import(request):
    """Landing page where user clicks 'Connect to Strava'."""
    return render(request, 'strava/strava_import.html')


@login_required
def strava_login(request):
    """Redirects user to Strava's OAuth page."""
    client_id = os.getenv('STRAVA_CLIENT_ID')
    # build_absolute_uri ensures we use your dev host+port
    redirect_uri = request.build_absolute_uri('/strava/callback/')
    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        "&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&scope=read,activity:read"
    )
    return redirect(auth_url)


@login_required
def strava_callback(request):
    """
    Strava redirects back here with ?code=…
    Exchange that code for an access_token, fetch activities, and save.
    """
    code = request.GET.get('code')
    if not code:
        # no code → bounce back to import page
        return redirect('strava.import')

    # Exchange code for token
    token_url = "https://www.strava.com/oauth/token"
    data = {
        'client_id': os.getenv('STRAVA_CLIENT_ID'),
        'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
        'code': code,
        'grant_type': 'authorization_code',
    }
    resp = requests.post(token_url, data=data)
    token_data = resp.json()
    access_token = token_data.get('access_token')
    if not access_token:
        # something went wrong
        return redirect('strava.import')

    # Fetch & save
    workouts = get_workouts(access_token)
    save_workouts(workouts, request.user)

    # show them their imported workouts
    return redirect('strava.workouts')


def get_workouts(access_token):
    """Pull recent activities from Strava API."""
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(url, headers=headers)
    return resp.json()


def save_workouts(workouts, user):
    """
    For each activity, update_or_create by (user_id, strava_id).
    If it's a new import, deduct its duration/calories from any matching goal.
    """
    for activity in workouts:
        strava_id = activity['id']
        defaults = {
            'name': activity.get('name'),
            'activity_type': activity.get('type'),
            'distance': activity.get('distance'),
            'moving_time': activity.get('moving_time'),
            'date': activity.get('start_date'),
            'calories': activity.get('calories', 0),
        }

        sa, created = StravaActivity.objects.update_or_create(
            user_id=user.id,
            strava_id=strava_id,
            defaults=defaults
        )

        if created:
            # If a goal mentions this activity type, deduct its time/calories
            goal = (
                Goal.objects
                .filter(user=user, text__icontains=defaults['activity_type'])
                .first()
            )
            if goal:
                goal.total_duration_seconds = max(
                    0, goal.total_duration_seconds - defaults['moving_time']
                )
                goal.calories_burnt_per_second += defaults['calories']
                goal.save()


@login_required
def show_workouts(request):
    """Show only the current user's imported workouts."""
    workouts = (
        StravaActivity.objects
        .filter(user_id=request.user.id)
        .order_by('-date')
    )
    return render(request, 'strava/show_workouts.html', {
        'workouts': workouts
    })
