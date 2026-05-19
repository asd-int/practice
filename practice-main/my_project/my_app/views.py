from datetime import timedelta
from django.db.models import Avg, IntegerField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Course,
    Enrollment,
    Exercise,
    Lecture,
    Progress,
    Quiz,
    Role,
    Role_Permission,
    Users,
    UserContentStatus,
)


# ==========================================
# ДЕТАЛЬНЫЙ ПРОСМОТР КУРСА И ДОБАВЛЕНИЕ МАТЕРИАЛОВ
# ==========================================
def course_detail_view(request, pk):
    course = get_object_or_404(Course, id=pk)
    lectures = Lecture.objects.filter(course_id=course)
    exercises = Exercise.objects.filter(course_id=course)
    quizzes = Quiz.objects.filter(course_id=course)

    # Списки выполненных ID (по умолчанию пустые)
    completed_lectures = []
    completed_exercises = []
    completed_quizzes = []

    # ИСПРАВЛЕНО: Безопасное получение роли в любом регистре и на двух языках
    current_role = str(request.session.get('role', '')).strip().lower()

    if current_role in ['student', 'студент']:
        user_id = request.session.get('user_id')

        # Принудительно приводим QuerySet к списку list() для корректной работы 'if id in ...' в шаблоне
        completed_lectures = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, lecture__isnull=False, is_completed=True
        ).values_list('lecture_id', flat=True))

        completed_exercises = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, exercise__isnull=False, is_completed=True
        ).values_list('exercise_id', flat=True))

        completed_quizzes = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, quiz__isnull=False, is_completed=True
        ).values_list('quiz_id', flat=True))

    # Передаем списки в контекст шаблона
    context = {
        'course': course,
        'lectures': lectures,
        'exercises': exercises,
        'quizzes': quizzes,
        'completed_lectures': completed_lectures,
        'completed_exercises': completed_exercises,
        'completed_quizzes': completed_quizzes,
    }
    return render(request, 'course_detail.html', context)


# ДОБАВЛЕНО: Функция обработки клика по чекбоксу и автоматического пересчета прогресса
def toggle_status_view(request, pk):
    current_role = str(request.session.get('role', '')).strip().lower()

    if request.method == "POST" and current_role in ['student', 'студент']:
        user_obj = get_object_or_404(Users, id=request.session.get('user_id'))
        course_obj = get_object_or_404(Course, id=pk)

        item_type = request.POST.get('item_type')  # 'lecture', 'exercise' или 'quiz'
        item_id = request.POST.get('item_id')

        # Динамически собираем параметры для поиска/создания записи
        filter_kwargs = {'user_id': user_obj, 'course_id': course_obj}
        filter_kwargs[f"{item_type}_id"] = item_id

        # Меняем статус на противоположный или создаем новый
        status_obj, created = UserContentStatus.objects.get_or_create(**filter_kwargs)
        if not created:
            status_obj.is_completed = not status_obj.is_completed
            status_obj.save()
        else:
            status_obj.is_completed = True
            status_obj.save()

        # --- АВТОМАТИЧЕСКИЙ ПЕРЕСЧЕТ ПРОГРЕССА ---
        # 1. Считаем общее количество материалов на курсе
        total_items = (
                Lecture.objects.filter(course_id=course_obj).count() +
                Exercise.objects.filter(course_id=course_obj).count() +
                Quiz.objects.filter(course_id=course_obj).count()
        )

        # 2. Считаем сколько из них отмечено этим студентом
        completed_items = UserContentStatus.objects.filter(
            user_id=user_obj, course_id=course_obj, is_completed=True
        ).count()

        # 3. Высчитываем процент выполнения
        progress_percent = int((completed_items / total_items) * 100) if total_items > 0 else 0

        # 4. Записываем обновленный процент в таблицу Progress (строкой, так как там CharField)
        progress_obj, _ = Progress.objects.get_or_create(user_id=user_obj, course_id=course_obj)
        progress_obj.progress_percent = str(progress_percent)
        progress_obj.save()

    return redirect('course_detail', pk=pk)



def add_content_view(request, pk):
    # Защита: только преподаватель может добавлять контент
    if request.session.get('role') != 'Teacher':
        return redirect('course_list')

    course_obj = get_object_or_404(Course, id=pk)

    if request.method == "POST":
        content_type = request.POST.get('content_type')  # 'lecture', 'exercise' или 'quiz'
        title = request.POST.get('title')
        description = request.POST.get('description')  # Для Exercise

        # Ловим загруженный файл (для Лекций и Заданий)
        uploaded_file = request.FILES.get('content_file')

        # Ловим ссылку (для Тестов)
        quiz_link = request.POST.get('link_quiz')

        if content_type == 'lecture':
            # В модели Lecture НЕТ поля description, убираем его отсюда
            Lecture.objects.create(
                lecture_title=title,
                content=uploaded_file,
                course_id=course_obj
            )

        elif content_type == 'exercise':
            due_date_input = request.POST.get('due_date')
            if not due_date_input:
                due_date_input = timezone.now().date() + timedelta(days=7)

            Exercise.objects.create(
                exercise_title=title,
                description=description,  # Тут поле есть
                content=uploaded_file,
                due_date=due_date_input,
                course_id=course_obj
            )

        elif content_type == 'quiz':
            # В модели Quiz вместо файла и описания нужно передавать обязательный link_quiz
            if not quiz_link:
                quiz_link = "#"  # Заглушка, если препод забыл вставить ссылку

            Quiz.objects.create(
                quiz_title=title,
                link_quiz=quiz_link,  # Передаем обязательную ссылку
                course_id=course_obj
            )

    return redirect('course_detail', pk=pk)


# ==========================================
# АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
# ==========================================


def login_view(request):
    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")

        # Ищем пользователя
        user = Users.objects.filter(
            username=username_input, password=password_input
        ).first()

        if user:
            # Фиксируем данные в сессии
            request.session["user_id"] = user.id
            request.session["username"] = user.username

            # ИСПРАВЛЕНО: Безопасное и строгое извлечение роли без падения в случайную запись
            if user.role_perm_id and user.role_perm_id.role_id:
                role_name = user.role_perm_id.role_id.role_name
            else:
                role_name = "Student"  # Если связи нет, то это точно базовый студент

            request.session["role"] = role_name
            return redirect("dashboard")
        else:
            return render(
                request, "login.html", {"error": "Неверный логин или пароль"}
            )

    return render(request, "login.html")

def register_view(request):
    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        chosen_role = request.POST.get("role")  # 'Student' или 'Teacher'

        if Users.objects.filter(username=username_input).exists():
            return render(
                request, "register.html", {"error": "Этот логин уже занят"}
            )

        # ИСПРАВЛЕНО: Ищем роль с учетом регистра и возможных вариантов (рус/eng)
        # Убираем опасный .first() без фильтрации!
        role_perm_obj = Role_Permission.objects.filter(
            role_id__role_name__iexact=chosen_role
        ).first()

        # Если на английском не нашли, пробуем найти на русском языке
        if not role_perm_obj:
            ru_role = "Студент" if chosen_role.lower() == "student" else "Преподаватель"
            role_perm_obj = Role_Permission.objects.filter(
                role_id__role_name__iexact=ru_role
            ).first()

        # Если даже после этого в базе нет настроенных ролей — выдаем ошибку,
        # вместо того чтобы скрытно делать пользователя преподавателем!
        if not role_perm_obj:
            return render(
                request, "register.html",
                {"error": f"Криcritical: Роль '{chosen_role}' не настроена в базе данных администратором."}
            )

        # Создаем запись в таблице Users
        new_user = Users.objects.create(
            username=username_input,
            password=password_input,
            first_name=first_name,
            last_name=last_name,
            role_perm_id=role_perm_obj,
        )

        # Автоматически логиним после регистрации
        request.session["user_id"] = new_user.id
        request.session["username"] = new_user.username
        request.session["role"] = role_perm_obj.role_id.role_name

        return redirect("dashboard")

    return render(request, "register.html")

def logout_view(request):
    # Очищаем сессию
    request.session.flush()
    return redirect("login")


# ==========================================
# 1. ЭКРАН: Дашборд
# ==========================================
def dashboard_view(request):
    courses_count = Course.objects.count()

    # Студенты: связываемся через имя поля 'role_perm_id', а внутри него — через 'role_id'
    students_count = Users.objects.filter(
        role_perm_id__role_id__role_name="Student"
    ).count()

    exercises_count = Exercise.objects.count()

    # Кастуем CharField в IntegerField на лету перед вычислением среднего значения
    avg_progress = (
        Progress.objects.aggregate(
            avg_res=Avg(Cast("progress_percent", output_field=IntegerField()))
        )["avg_res"]
        or 0
    )

    context = {
        "courses_count": courses_count,
        "students_count": students_count,
        "exercises_count": exercises_count,
        "avg_progress": round(avg_progress, 1),
    }
    return render(request, "dashboard.html", context)


# ==========================================
# 2. ЭКРАН: Список курсов + Добавление
# ==========================================
def course_list_view(request):
    search_query = request.GET.get("search", "")
    courses = Course.objects.all()

    if search_query:
        courses = courses.filter(course_title__icontains=search_query)

    # Получаем ID текущего залогиненного пользователя
    current_user_id = request.session.get('user_id')
    current_user = Users.objects.filter(id=current_user_id).first()

    course_data = []
    for course in courses:
        students_enrolled = Enrollment.objects.filter(course_id=course).count()

        # ИСПРАВЛЕНО: Считаем прогресс КОРЕКТНО — только для ТЕКУЩЕГО студента
        if current_user:
            progress_obj = Progress.objects.filter(
                course_id=course,
                user_id=current_user  # Фильтруем строго по конкретному студенту!
            ).first()

            # Если запись нашли, берем её процент, иначе 0
            try:
                avg_course_progress = int(progress_obj.progress_percent) if progress_obj else 0
            except (ValueError, TypeError):
                avg_course_progress = 0
        else:
            avg_course_progress = 0

        course_data.append(
            {
                "instance": course,
                "students_count": students_enrolled,
                "progress": avg_course_progress,  # Теперь тут личный прогресс
            }
        )

    return render(
        request,
        "courses.html",
        {"courses": course_data, "search_query": search_query},
    )

def course_add_view(request):
    # Защита: только преподаватель может создавать курсы
    if request.session.get("role") != "Teacher":
        return redirect("course_list")

    if request.method == "POST":
        title = request.POST.get("course_title")
        desc = request.POST.get("description")
        start = request.POST.get("start_date")
        end = request.POST.get("end_date")
        author_id = request.POST.get("author_id")

        # Получаем объект преподавателя
        author_obj = get_object_or_404(Users, id=author_id)

        # Передаем объект в поле user_id (так как это ForeignKey)
        Course.objects.create(
            course_title=title,
            description=desc,
            start_date=start,
            end_date=end,
            user_id=author_obj,
        )

    return redirect("course_list")


# ==========================================
# 3. ЭКРАН: Список студентов + Добавление
# ==========================================
def student_list_view(request):
    search_query = request.GET.get("search", "")

    # select_related принимает именно названия полей в Python-коде класса.
    enrollments = Enrollment.objects.select_related("user_id", "course_id").all()

    if search_query:
        enrollments = enrollments.filter(user_id__last_name__icontains=search_query)

    # Формируем структуру данных для таблицы
    students_table = []
    for emp in enrollments:
        current_user = emp.user_id
        current_course = emp.course_id

        progress_obj = Progress.objects.filter(
            user_id=current_user, course_id=current_course
        ).first()

        # Безопасно парсим строку в число для отображения в UIkit-progressbar-е
        try:
            progress = int(progress_obj.progress_percent) if progress_obj else 0
        except (ValueError, TypeError):
            progress = 0

        students_table.append(
            {
                "student_id": current_user.id,
                "full_name": f"{current_user.last_name} {current_user.first_name}",
                "course_title": current_course.course_title,
                "email": f"{current_user.username}@example.com",
                "progress": progress,
            }
        )

    all_courses = Course.objects.all()

    context = {
        "students": students_table,
        "search_query": search_query,
        "all_courses": all_courses,
    }
    return render(request, "students.html", context)


def student_add_view(request):
    # Защита: только преподаватель может зачислять новых студентов через админку
    if request.session.get("role") != "Teacher":
        return redirect("student_list")

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        password = request.POST.get("password")
        course_id = request.POST.get("course_id")
        selected_role_perm_id = request.POST.get("role_perm_id")

        # Получаем объект прав
        role_perm_obj = get_object_or_404(Role_Permission, id=selected_role_perm_id)

        # 1. Создаем пользователя, передавая объект в поле role_perm_id
        new_student = Users.objects.create(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role_perm_id=role_perm_obj,
        )

        # 2. Находим выбранный курс
        course_obj = get_object_or_404(Course, id=course_id)

        # Зачисляем на курс, используя названия полей (user_id и course_id)
        Enrollment.objects.create(
            user_id=new_student, course_id=course_obj, status="active"
        )

        # 3. Создаем базовый нулевой прогресс (строкой '0', так как в БД тип CharField)
        Progress.objects.create(
            user_id=new_student, course_id=course_obj, progress_percent="0"
        )

    return redirect("student_list")


# ==========================================
# 4. ЭКРАН: Профиль студента
# ==========================================
def student_detail_view(request, pk):
    student = get_object_or_404(Users, id=pk)

    # Фильтруем зачисления по полю user_id
    enrolled_courses = Enrollment.objects.filter(user_id=student).select_related(
        "course_id"
    )

    # Для шаблона перепакуем данные, чтобы в цикле было удобно брать .course
    courses_list = [emp.course_id for emp in enrolled_courses]

    context = {
        "student": student,
        "enrolled_courses": courses_list,
    }
    return render(request, "student_detail.html", context)


def delete_content_view(request, pk, content_type, content_id):


    if content_type == 'lecture':
        deleted_count, _ = Lecture.objects.filter(id=content_id).delete()
    elif content_type == 'exercise':
        deleted_count, _ = Exercise.objects.filter(id=content_id).delete()
    elif content_type == 'quiz':
        deleted_count, _ = Quiz.objects.filter(id=content_id).delete()


    return redirect('course_detail', pk=pk)