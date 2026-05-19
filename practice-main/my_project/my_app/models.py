from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class Role(models.Model):
    role_name = models.CharField(max_length = 100, null = False)
    description = models.CharField(max_length = 300, null = True)

class Permission(models.Model):
    permission_name = models.CharField(max_length = 100, null = False)
    description = models.CharField(max_length = 300, null = True)

class Role_Permission(models.Model):
    role_id = models.ForeignKey(Role, on_delete = models.CASCADE)
    permission_id = models.ForeignKey(Permission, on_delete = models.CASCADE)

class Users(models.Model):
    username = models.CharField(max_length = 100, null = False)
    password = models.CharField(max_length = 100, null = False)
    first_name = models.CharField(max_length = 100, null = False)
    last_name = models.CharField(max_length = 100, null = False)
    role_perm_id = models.ForeignKey(Role_Permission, on_delete = models.CASCADE)
    avatar = models.FileField(upload_to = 'avatars/', null = False)
    created_at = models.DateTimeField(auto_now_add = True)

class Course(models.Model):
    course_title = models.CharField(max_length = 100, null = False)
    description = models.CharField(max_length = 300, null = True)
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    start_date = models.DateField(null = False)
    end_date = models.DateField(null = False)

class Lecture(models.Model):
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    lecture_title = models.CharField(max_length = 100, null = True)
    content = models.FileField(upload_to='uploads/', null = False)
    created_at = models.DateTimeField(auto_now_add = True)

class Exercise(models.Model):
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    exercise_title = models.CharField(max_length = 100, null = False)
    description = models.CharField(max_length = 300, null = True)
    content = models.FileField(upload_to='uploads/', null = False)
    due_date = models.DateField(null = False)
    created_at = models.DateTimeField(auto_now_add = True)

class Quiz(models.Model):
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    quiz_title = models.CharField(max_length = 100, null = False)
    link_quiz = models.CharField(max_length = 100, null = False)
    created_at = models.DateTimeField(auto_now_add = True)


class UserContentStatus(models.Model):
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, null=True, blank=True)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True)

    is_completed = models.BooleanField(default=False)

class Marks (models.Model):
    exercise_id = models.ForeignKey(Exercise,null = True, on_delete = models.CASCADE)
    quiz_id = models.ForeignKey(Quiz,null = True, on_delete = models.CASCADE)
    lecture_id = models.ForeignKey(Lecture,null = True, on_delete = models.CASCADE)
    mark = models.CharField(max_length = 100, null = False)

class Gradebook(models.Model):
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    mark_id = models.ForeignKey(Marks, on_delete = models.CASCADE)
    graded_at = models.DateField(null = False)

class Report(models.Model):
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    created_at = models.DateTimeField(auto_now_add = True)
    report_text = models.CharField(max_length = 300, null = False)

class Progress(models.Model):
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    progress_percent = models.IntegerField(default=0)

class Enrollment(models.Model):
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete = models.CASCADE)
    enrolled_at = models.DateField(auto_now_add = True, null = False)
    status = models.CharField(max_length = 100, null = False)

class Answer_Exercise(models.Model):
    exercise_id = models.ForeignKey(Exercise, on_delete = models.CASCADE)
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    answer_text = models.CharField(max_length = 300, null = False)
    answer_content = models.FileField(upload_to = 'uploads/', null = False)

class Comments(models.Model):
    answer_id = models.ForeignKey(Answer_Exercise, on_delete = models.CASCADE)
    user_id = models.ForeignKey(Users, on_delete = models.CASCADE)
    comment_text = models.CharField(max_length = 300, null = False)
    created_at = models.DateTimeField(auto_now_add = True)