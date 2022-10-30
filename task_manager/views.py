import datetime
import json
import random

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.core.mail import send_mail

from reports.models import ProjectInfo
from .models import Task, Project


class Projects(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        user = request.user
        projects = Project.objects.all()
        list = []

        for p in projects:
            if p.owner == user or user.id in p.get_members():
                list.append(ProjectInfo(p))

        data = {"user": user,
                "first": user.username[0],
                "other_users": User.objects.filter(~Q(id=user.id)).all(),
                "projects": list,
                }
        return render(request, 'projects.html', data)

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('signIn')

        name = request.POST['name']
        description = request.POST['desc']
        details = request.POST['details']
        owner = request.user
        user_ids = request.POST.getlist('users', [])

        ids = []
        for id in user_ids:
            ids.append(int(id))

        n = random.randint(1, 6)
        pf_url = f'/media/project-logos/{n}.png'

        proj = Project.objects.create(name=name, description=description, details=details, owner=owner,
                                      members=json.dumps(ids), profile_photo=pf_url)
        proj.save()

        return redirect('boards')


class MangeProject(View):
    def post(self, request, id):
        Project.objects.filter(id=id).delete()

        response = JsonResponse({"message": "OK"})
        response.status_code = 200
        return response


class Tasks(View):
    def get(self, request, id):
        if not request.user.is_authenticated:
            return redirect("signIn")

        proj = Project.objects.filter(id=id).first()
        user = request.user
        users = User.objects.filter(Q(id__in=proj.get_members()) | Q(id=proj.owner.id))
        tasks_urgent = proj.task_set.all().filter(priority="URGENT")
        tasks_high=proj.task_set.all().filter(priority="HIGH")
        tasks_medium=proj.task_set.all().filter(priority="MEDIUM")
        tasks_low=proj.task_set.all().filter(priority="LOW")
        # print(tasks_urgent, tasks_high, tasks_low, tasks_medium, tasks_low)
        data = {"user": user,
                "first": user.username[0],
                "other_users": users,
                #"tasks": proj.task_set.all(),
                'tasks': tasks_urgent | tasks_high | tasks_medium | tasks_low,
                'proj': proj,
                "can_add": user == proj.owner
                }
        print(data)
        return render(request, 'tasks.html', data)

    def post(self, request, id):
        if not request.user.is_authenticated:
            return redirect('signIn')

        name = request.POST['name']
        description = request.POST['desc']
        assigned_to = request.POST['users']
        status = 'T'
        end_time = request.POST['date']
        priority = request.POST['priority']
        resource_file = request.FILES["resource-file"]

        task = Task(name=name, description=description, assigned_to_id=assigned_to, status=status,
                    end_time=end_time, project_id=id, resource_file=resource_file, priority=priority)
        task.save()

        print(assigned_to)

        user = User.objects.get(id=assigned_to)
        email = user.email
        subject ='You are assigned a task'
        message1=f'''Hello {str(user.username)} ,

You have been assigned a task, {str(name)}.
Description : {str(description)}.
Assigned By : {str(request.user)}.

Resolve any further queries from {str(request.user)}. Make sure to finish it by {str(end_time)}.
Much appreciated - Task Manager

THANK YOU!!
'''
        send_mail(subject,message1,'chatbot.projectmanager@gmail.com',[email])

        return redirect('tasks', id=id)


class ManegeTasks(View):
    def post(self, request, id):
        if not request.user.is_authenticated:
            response = JsonResponse({"error": "Invalid User"})
            response.status_code = 403
            return response

        user = request.user

        type = request.POST['type']
        if type == 'edit_status':
            task_id = request.POST['task_id']
            status = request.POST['board_id']

            task = Task.objects.filter(id=task_id).first()

            if status in ['O', 'B', 'L'] or task.status in ['O', 'B', 'L']:
                if user == task.project.owner:
                    task.status = status
                    task.save()

                else:
                    response = JsonResponse({"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response
            else:
                if user == task.assigned_to or user == task.project.owner:
                    task.status = status
                    if status == 'D':
                        task.start_time = datetime.datetime.today().date()
                    task.save()
                else:
                    response = JsonResponse({"error": "You Do Not Have Permission"})
                    response.status_code = 403
                    return response

            response = JsonResponse({"message": "OK"})
            response.status_code = 200
            return response

        if type == 'edit_end_time':

            task_id = request.POST['task_id']
            end_time = request.POST['new_end_time']

            task = Task.objects.filter(id=task_id).first()

            if user == task.project.owner:
                task.end_time = end_time
                task.save()

                response = JsonResponse({"message": "OK"})
                response.status_code = 200
                return response

            else:
                response = JsonResponse({"error": "You Do Not Have Permission"})
                response.status_code = 403
                return response
