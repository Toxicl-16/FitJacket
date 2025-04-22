from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Goal, Profile
from django.contrib import messages
from django.utils import timezone
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()


@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if (Goal.expired_goals(request.user) > 0):
        profile.current_streak = 0
        profile.save()
        return redirect('Dashboard')

    if request.method == 'POST':
        if 'submit_goal' in request.POST:
            text = request.POST.get('user_input_field')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            if end_date <= start_date:
                messages.error(request, "End date cannot be before or on the start date.")
            elif text and len(text) <= 100:
                goal_format = text_formatting(text)
                goal_text = goal_format[0] + " - " + goal_format[1] + " minutes"
                start_date = timezone.datetime.strptime(start_date, "%Y-%m-%d")
                end_date = timezone.datetime.strptime(end_date, "%Y-%m-%d")

                create_goal(request.user, goal_text, start_date, end_date)

            else:
                messages.error(request, "Goal must be 100 characters or less")

        elif 'complete_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.completed = True
            goal.abandoned = False
            goal.save()
            messages.success(request, "Goal marked as complete!")
            profile.current_streak += 1
            profile.save()
            return redirect('Dashboard')

        elif 'abandon_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.abandoned = True
            goal.completed = False
            goal.save()
            messages.success(request, "Goal abandoned!")
            profile.current_streak = 0
            profile.save()
            return redirect('Dashboard')
        elif 'favorite_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.favorite = True
            goal.save()
            messages.success(request, "Goal favorited!")
            return redirect('favorite/')

    current_goals = Goal.objects.filter(user=request.user, completed=False, abandoned=False)
    completed_goals_count = Goal.objects.filter(user=request.user, completed=True).count()
    abandoned_goals_count = Goal.objects.filter(user=request.user, abandoned=True).count()
    remaining_goals_count = Goal.objects.filter(user=request.user, completed=False, abandoned=False).count()
    return render(request, 'dashboard/goals.html', {
        'user_inputs': current_goals,
        'completed_goals_count': completed_goals_count,
        'abandoned_goals_count': abandoned_goals_count,
        'remaining_goals_count': remaining_goals_count,
        'streak': profile.current_streak
    })


@login_required
def goal_history(request):
    completed_goals = Goal.objects.filter(user=request.user, completed=True)
    abandoned_goals = Goal.objects.filter(user=request.user, abandoned=True)

    return render(request, 'dashboard/goal-history.html', {
        'completed_goals': completed_goals,
        'abandoned_goals': abandoned_goals,
    })


@login_required
def mark_favorite(request):
    if request.method == 'POST':

        if 'unfavorite_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.favorite = False
            goal.save()
            messages.success(request, "Goal Unfavorited!")
            return redirect('FavoriteHistory')

        elif 'add_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            time_diff = goal.end_date - goal.start_date
            start = timezone.now()
            end = start + time_diff

            create_goal(request.user, goal.text, start, end)

            messages.success(request, "Goal added to Dashbord!")
            return redirect('Dashboard')

    favorite_goals = Goal.objects.filter(user=request.user, favorite=True)
    return render(request, 'dashboard/favorite.html', {
        'favorite_goals': favorite_goals
    })


def create_goal(user, text, start_date, end_date):
    if timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)
    if timezone.is_naive(end_date):
        end_date = timezone.make_aware(end_date)

    return Goal.objects.create(
        text=text,
        user=user,
        start_date=start_date,
        end_date=end_date
    )


def text_formatting(text):
    try:
        client = genai.Client(api_key=os.getenv('GENAI_API_KEY'))
        contents = (
            "You are to extract the type of exercise and duration from the user's sentence. "
            "Only output in this exact format: '[ExerciseType]: [DurationInMinutes]'. "
            "If no valid exercise is found but time is found, output 'Break: [DurationInMinutes]'. "
            "If no valid exercise and time is found, output 'Break: 0'. "
            "No context. Only use this input: "
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=contents + " " + text
        )

        if ":" in response.text:
            return response.text.split(": ")
        else:
            return ["Break", "0"]
    except Exception as e:
        print(f"Error with AI request: {e}")
        return ["Break", "0"]
