# my_app/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Users, Course


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = Users.objects.get(username=username, password=password)

            # Получаем роль пользователя
            role_perm = user.role_perm_id
            role = role_perm.role_id

            # Сохраняем в сессию
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['role'] = role.role_name  # Сохраняем роль

            return redirect('courses')  # Перенаправляем на страницу курсов
        except Users.DoesNotExist:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


def courses_view(request):
    # Проверяем авторизацию
    if not request.session.get('user_id'):
        return redirect('login')

    # Получаем все курсы
    courses = Course.objects.all()

    # Получаем роль пользователя
    user_role = request.session.get('role')

    return render(request, 'courses.html', {
        'courses': courses,
        'role': user_role,
        'username': request.session.get('username')
    })


def add_course_view(request):
    # Проверяем авторизацию
    if not request.session.get('user_id'):
        return redirect('login')

    # Только преподаватель может добавить курс
    if request.session.get('role') != 'Преподаватель':
        messages.error(request, 'У вас нет прав на добавление курса')
        return redirect('courses')

    if request.method == 'POST':
        course_title = request.POST.get('course_title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        Course.objects.create(
            course_title=course_title,
            description=description,
            user_id_id=request.session.get('user_id'),
            start_date=start_date,
            end_date=end_date
        )
        messages.success(request, 'Курс успешно добавлен!')
        return redirect('courses')

    return render(request, 'add_course.html')