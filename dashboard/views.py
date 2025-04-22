from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Goal, Profile, Progress
from django.contrib import messages
from django.utils import timezone
from openai import OpenAI
from dotenv import load_dotenv
import json
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
                exercise_type, duration_minutes, calories_per_minute = text_formatting(text)
                goal_text = f"{exercise_type} - {duration_minutes} minutes"
                start_date = timezone.make_aware(timezone.datetime.strptime(start_date, "%Y-%m-%d"))
                end_date = timezone.make_aware(timezone.datetime.strptime(end_date, "%Y-%m-%d"))

                Goal.objects.create(
                    text=goal_text,
                    user=request.user,
                    start_date=start_date,
                    end_date=end_date,
                    total_duration_seconds=duration_minutes * 60,
                    calories_burnt_per_second=calories_per_minute / 60
                )
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
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Prompt the AI to extract exercise, duration, AND calories per minute
        system_prompt = (
            "You will extract exercise type, duration in minutes, and estimate calories burned per minute. "
            "Return in JSON format like this: "
            "{\"exercise\": \"Jump Rope\", \"duration_minutes\": 20, \"calories_per_minute\": 12}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=100,
        )

        response_text = response.choices[0].message.content.strip()

        parsed = json.loads(response_text)

        exercise_type = parsed.get("exercise", "Unknown Exercise")
        duration_minutes = parsed.get("duration_minutes", 0)
        calories_per_minute = parsed.get("calories_per_minute", 0)

        return exercise_type, duration_minutes, calories_per_minute

    except Exception as e:
        print(f"Error with AI request: {e}")
        return "Break", 0, 0



@login_required
def progress_view(request):
    user_progress = Progress.objects.filter(user=request.user)
    completed = Goal.objects.filter(user=request.user, completed=True).count()
    remaining = Goal.objects.filter(user=request.user, completed=False, abandoned=False).count()
    abandoned = Goal.objects.filter(user=request.user, abandoned=True).count()

    total_goals = completed + remaining + abandoned
    if total_goals > 0:
        total_completion_percentage = round((completed / total_goals) * 100)
        total_remaining_percentage = 100 - total_completion_percentage
    else:
        total_completion_percentage = 0
        total_remaining_percentage = 100

    return render(request, 'dashboard/progress.html', {
        'progress_data': user_progress,
        'completed_goals_count': completed,
        'remaining_goals_count': remaining,
        'abandoned_goals_count': abandoned,
        'total_completion_percentage': total_completion_percentage,
        'total_remaining_percentage': total_remaining_percentage,
    })

@login_required
def start_goal(request, goal_id):
    goal = Goal.objects.get(id=goal_id)

    return render(request, 'dashboard/start_goal.html', {
        'goal': goal,
    })

@login_required
def complete_goal(request):
    if request.method == 'POST':
        goal_id = request.POST.get('goal_id')
        calories_burned = request.POST.get('calories_burned')

        goal = Goal.objects.get(id=goal_id)

        Progress.objects.create(
            user=request.user,
            goal_name=goal.text,
            progress_value=round(float(calories_burned)),
            target_value=goal.total_duration_seconds,
        )

        goal.completed = True
        goal.save()

        return redirect('progress')


