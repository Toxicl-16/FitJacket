from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Goal
from django.contrib import messages
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


@login_required
def dashboard(request):
    if request.method == 'POST':
        if 'submit_goal' in request.POST:
            text = request.POST.get('user_input_field')
            if text and len(text) <= 100:
                goal_format = text_formatting(text)
                goal_text = goal_format[0] + " - " + goal_format[1] + " minutes"
                Goal.objects.create(text=goal_text, user=request.user)
                messages.success(request, "Goal added successfully!")
            else:
                messages.error(request, "Goal must be 100 characters or less")

        elif 'complete_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.completed = True
            goal.abandoned = False
            goal.save()
            messages.success(request, "Goal marked as complete!")
            return redirect('Dashboard')

        elif 'abandon_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = Goal.objects.get(id=goal_id)
            goal.abandoned = True
            goal.completed = False
            goal.save()
            messages.success(request, "Goal abandoned!")
            return redirect('Dashboard')

    current_goals = Goal.objects.filter(user=request.user, completed=False, abandoned=False)
    completed_goals_count = Goal.objects.filter(user=request.user, completed=True).count()
    abandoned_goals_count = Goal.objects.filter(user=request.user, abandoned=True).count()
    remaining_goals_count = Goal.objects.filter(user=request.user, completed=False, abandoned=False).count()

    return render(request, 'dashboard/goals.html', {
        'user_inputs': current_goals,
        'completed_goals_count': completed_goals_count,
        'abandoned_goals_count': abandoned_goals_count,
        'remaining_goals_count': remaining_goals_count,
    })


@login_required
def goal_history(request):
    completed_goals = Goal.objects.filter(user=request.user, completed=True)
    abandoned_goals = Goal.objects.filter(user=request.user, abandoned=True)

    return render(request, 'dashboard/goal-history.html', {
        'completed_goals': completed_goals,
        'abandoned_goals': abandoned_goals,
    })


def text_formatting(text):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        contents = (
            "You are to extract the type of exercise and duration from the user's sentence. "
            "Only output in this exact format: '[ExerciseType]: [DurationInMinutes]'. "
            "If no valid exercise is found but time is found, output 'Break: [DurationInMinutes]'. "
            "If no valid exercise and time is found, output 'Break: 0'. "
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=50,
        )

        response_text = response.choices[0].message.content.strip()

        if ":" in response.text:
            return response.text.split(": ")
        else:
            return ["Break", "0"]
    except Exception as e:
        print(f"Error with AI request: {e}")
        return ["Break", "0"]
