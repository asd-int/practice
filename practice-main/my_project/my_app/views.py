from datetime import timedelta, date
from django.db.models import Avg, IntegerField, Value, Q
from django.db.models.functions import Cast, Concat
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages

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
    Report,
    Answer_Exercise,
)


def add_content_view(request, pk):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['teacher', 'преподаватель']:
        messages.error(request, "У вас нет прав на добавление материалов.")
        return redirect('course_list')

    course_obj = get_object_or_404(Course, id=pk)

    if request.method == "POST":
        content_type = request.POST.get('content_type')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()

        uploaded_file = request.FILES.get('content_file')
        quiz_link = request.POST.get('link_quiz', '').strip()
        due_date_input = request.POST.get('due_date')

        try:
            if content_type == 'lecture':
                if not title or not uploaded_file:
                    raise ValueError("Название и файл лекции обязательны.")

                Lecture.objects.create(
                    lecture_title=title,
                    content=uploaded_file,
                    course_id=course_obj
                )
                messages.success(request, "Лекция успешно добавлена!")

            elif content_type == 'exercise':
                if not title or not description or not uploaded_file:
                    raise ValueError("Название, описание и файл задания обязательны.")

                if due_date_input:
                    due_date = date.fromisoformat(due_date_input)
                else:
                    due_date = timezone.now().date() + timedelta(days=7)

                Exercise.objects.create(
                    exercise_title=title,
                    description=description,
                    content=uploaded_file,
                    due_date=due_date,
                    course_id=course_obj
                )
                messages.success(request, "Задание успешно добавлено!")

            elif content_type == 'quiz':
                if not title or not quiz_link:
                    raise ValueError("Название и ссылка на тест обязательны.")

                Quiz.objects.create(
                    quiz_title=title,
                    link_quiz=quiz_link,
                    course_id=course_obj
                )
                messages.success(request, "Тест успешно добавлен!")
            else:
                raise ValueError(f"Неизвестный тип контента: {content_type}")

            total_items = (
                    Lecture.objects.filter(course_id=course_obj).count() +
                    Exercise.objects.filter(course_id=course_obj).count() +
                    Quiz.objects.filter(course_id=course_obj).count()
            )

            enrollments = Enrollment.objects.filter(course_id=course_obj)
            for enrollment in enrollments:
                student = enrollment.user_id
                completed_items = UserContentStatus.objects.filter(
                    user_id=student, course_id=course_obj, is_completed=True
                ).count()

                progress_percent = int((completed_items / total_items) * 100) if total_items > 0 else 0

                progress_obj, _ = Progress.objects.get_or_create(user_id=student, course_id=course_obj)
                progress_obj.progress_percent = str(progress_percent)
                progress_obj.save()

        except Exception as e:
            messages.error(request, f"Ошибка при добавлении: {str(e)}")

    return redirect('course_detail', pk=pk)


def course_add_view(request):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['teacher', 'преподаватель']:
        return redirect('course_list')

    if request.method != "POST":
        return redirect('course_list')

    title = request.POST.get("course_title")
    desc = request.POST.get("description")
    start = request.POST.get("start_date")
    end = request.POST.get("end_date")
    author_id = request.POST.get("author_id")

    selected_student_ids = request.POST.getlist("students")
    author_obj = get_object_or_404(Users, id=author_id)

    new_course = Course.objects.create(
        course_title=title,
        description=desc,
        start_date=start,
        end_date=end,
        user_id=author_obj,
    )

    if selected_student_ids:
        for student_id in selected_student_ids:
            student_obj = Users.objects.filter(id=student_id).first()
            if student_obj:
                Enrollment.objects.get_or_create(
                    user_id=student_obj,
                    course_id=new_course,
                    defaults={"status": "active"}
                )
                Progress.objects.get_or_create(
                    user_id=student_obj,
                    course_id=new_course,
                    defaults={"progress_percent": "0"}
                )

    return redirect('course_detail', pk=new_course.id)


def course_detail_view(request, pk):
    course = get_object_or_404(Course, id=pk)
    lectures = Lecture.objects.filter(course_id=course)
    exercises = Exercise.objects.filter(course_id=course)
    quizzes = Quiz.objects.filter(course_id=course)

    completed_lectures = []
    completed_exercises = []
    completed_quizzes = []

    current_role = str(request.session.get('role', '')).strip().lower()
    user_id = request.session.get('user_id')

    if current_role in ['student', 'студент']:
        completed_lectures = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, lecture__isnull=False, is_completed=True
        ).values_list('lecture_id', flat=True))

        completed_exercises = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, exercise__isnull=False, is_completed=True
        ).values_list('exercise_id', flat=True))

        completed_quizzes = list(UserContentStatus.objects.filter(
            user_id=user_id, course_id=course, quiz__isnull=False, is_completed=True
        ).values_list('quiz_id', flat=True))

        submitted_answers = Answer_Exercise.objects.filter(
            exercise_id__course_id=course, user_id=user_id
        ).select_related('user_id')
    else:
        submitted_answers = Answer_Exercise.objects.filter(
            exercise_id__course_id=course
        ).select_related('user_id')

    context = {
        'course': course,
        'lectures': lectures,
        'exercises': exercises,
        'quizzes': quizzes,
        'completed_lectures': completed_lectures,
        'completed_exercises': completed_exercises,
        'completed_quizzes': completed_quizzes,
        'submitted_answers': submitted_answers,
    }

    return render(request, 'course_detail.html', context)


from django.core.paginator import Paginator # 1. Импортируйте Paginator

def course_list_view(request):
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "all")

    courses = Course.objects.all()

    if search_query:
        courses = courses.filter(course_title__icontains=search_query)

    today = date.today()
    if status_filter == 'active':
        courses = courses.filter(start_date__lte=today, end_date__gte=today)
    elif status_filter == 'past':
        courses = courses.filter(end_date__lt=today)

    current_user_id = request.session.get('user_id')
    current_user = Users.objects.filter(id=current_user_id).first()

    current_role = str(request.session.get('role', '')).strip().lower()

    course_data = []
    for course in courses:
        enrollments = Enrollment.objects.filter(course_id=course).select_related('user_id')
        students_enrolled = enrollments.count()
        course_students = [emp.user_id for emp in enrollments if emp.user_id]

        if current_user:
            progress_obj = Progress.objects.filter(course_id=course, user_id=current_user).first()
            avg_course_progress = int(progress_obj.progress_percent) if progress_obj and progress_obj.progress_percent else 0
        else:
            avg_course_progress = 0

        course_data.append({
            "instance": course,
            "students_count": students_enrolled,
            "students_list": course_students,
            "progress": avg_course_progress,
        })

    # 2. Настройка пагинации (3 курса на страницу)
    paginator = Paginator(course_data, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "courses.html",
        {
            "courses": page_obj,  # 3. Передаем объект страницы
            "search_query": search_query,
        },
    )


def dashboard_view(request):
    courses_count = Course.objects.count()

    students_count = Users.objects.filter(
        role_perm_id__role_id__role_name="Student"
    ).count()

    exercises_count = Exercise.objects.count()

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


def delete_content_view(request, pk, content_type, content_id):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['teacher', 'преподаватель']:
        messages.error(request, "У вас нет прав на удаление материалов.")
        return redirect('course_detail', pk=pk)

    try:
        if content_type == 'lecture':
            UserContentStatus.objects.filter(lecture_id=content_id).delete()
            Lecture.objects.filter(id=content_id, course_id=pk).delete()

        elif content_type == 'exercise':
            UserContentStatus.objects.filter(exercise_id=content_id).delete()
            Answer_Exercise.objects.filter(exercise_id=content_id).delete()
            Exercise.objects.filter(id=content_id, course_id=pk).delete()

        elif content_type == 'quiz':
            UserContentStatus.objects.filter(quiz_id=content_id).delete()
            Quiz.objects.filter(id=content_id, course_id=pk).delete()

        course_obj = Course.objects.filter(id=pk).first()
        if course_obj:
            total_items = (
                    Lecture.objects.filter(course_id=course_obj).count() +
                    Exercise.objects.filter(course_id=course_obj).count() +
                    Quiz.objects.filter(course_id=course_obj).count()
            )

            enrollments = Enrollment.objects.filter(course_id=course_obj)
            for enrollment in enrollments:
                student = enrollment.user_id
                completed_items = UserContentStatus.objects.filter(
                    user_id=student, course_id=course_obj, is_completed=True
                ).count()

                new_percent = int((completed_items / total_items) * 100) if total_items > 0 else 0

                progress_obj, _ = Progress.objects.get_or_create(user_id=student, course_id=course_obj)
                progress_obj.progress_percent = str(new_percent)
                progress_obj.save()

            messages.success(request, "Материал успешно удален, прогресс студентов пересчитан.")

    except Exception as e:
        messages.error(request, f"Не удалось удалить контент: {str(e)}")

    return redirect('course_detail', pk=pk)


def submit_answer_view(request, pk, exercise_id):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['student', 'студент']:
        messages.error(request, "Только студенты могут сдавать работы.")
        return redirect('course_detail', pk=pk)

    if request.method == "POST":
        uploaded_file = request.FILES.get('answer_file')
        answer_text = request.POST.get('answer_text', '').strip()

        if not uploaded_file:
            messages.error(request, "Необходимо выбрать файл с ответом.")
            return redirect('course_detail', pk=pk)

        user_obj = get_object_or_404(Users, id=request.session.get('user_id'))
        exercise_obj = get_object_or_404(Exercise, id=exercise_id)

        Answer_Exercise.objects.create(
            exercise_id=exercise_obj,
            user_id=user_obj,
            answer_text=answer_text,
            answer_content=uploaded_file
        )

        course_obj = get_object_or_404(Course, id=pk)
        status_obj, _ = UserContentStatus.objects.get_or_create(
            user_id=user_obj,
            course_id=course_obj,
            exercise=exercise_obj
        )
        status_obj.is_completed = True
        status_obj.save()

        total_items = (
                Lecture.objects.filter(course_id=course_obj).count() +
                Exercise.objects.filter(course_id=course_obj).count() +
                Quiz.objects.filter(course_id=course_obj).count()
        )
        completed_items = UserContentStatus.objects.filter(
            user_id=user_obj, course_id=course_obj, is_completed=True
        ).count()

        progress_percent = int((completed_items / total_items) * 100) if total_items > 0 else 0
        progress_obj, _ = Progress.objects.get_or_create(user_id=user_obj, course_id=course_obj)
        progress_obj.progress_percent = str(progress_percent)
        progress_obj.save()

        messages.success(request, "Ответ на задание успешно отправлен!")

    return redirect('course_detail', pk=pk)


def login_view(request):
    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")

        user = Users.objects.filter(
            username=username_input, password=password_input
        ).first()

        if user:
            request.session["user_id"] = user.id
            request.session["username"] = user.username

            if user.role_perm_id and user.role_perm_id.role_id:
                role_name = user.role_perm_id.role_id.role_name
            else:
                role_name = "Student"

            request.session["role"] = role_name
            return redirect("dashboard")
        else:
            return render(
                request, "login.html", {"error": "Неверный логин или пароль"}
            )

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        username_input = request.POST.get("username")
        password_input = request.POST.get("password")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        chosen_role = request.POST.get("role")

        if Users.objects.filter(username=username_input).exists():
            return render(
                request, "register.html", {"error": "Этот логин уже занят"}
            )

        role_perm_obj = Role_Permission.objects.filter(
            role_id__role_name__iexact=chosen_role
        ).first()

        if not role_perm_obj:
            ru_role = "Студент" if chosen_role.lower() == "student" else "Преподаватель"
            role_perm_obj = Role_Permission.objects.filter(
                role_id__role_name__iexact=ru_role
            ).first()

        if not role_perm_obj:
            return render(
                request, "register.html",
                {"error": f"Роль '{chosen_role}' не настроена в базе данных администратором."}
            )

        new_user = Users.objects.create(
            username=username_input,
            password=password_input,
            first_name=first_name,
            last_name=last_name,
            role_perm_id=role_perm_obj,
        )

        request.session["user_id"] = new_user.id
        request.session["username"] = new_user.username
        request.session["role"] = role_perm_obj.role_id.role_name

        return redirect("dashboard")

    return render(request, "register.html")


def report_add_view(request):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['teacher', 'преподаватель']:
        messages.error(request, "У вас нет прав на создание отчетов.")
        return redirect("report_list")

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        course_id = request.POST.get("course_id")
        report_text = request.POST.get("report_text", "").strip()

        if not report_text:
            messages.error(request, "Текст отчета не может быть пустым.")
            return redirect("report_list")

        student_obj = get_object_or_404(Users, id=student_id)
        course_obj = get_object_or_404(Course, id=course_id)

        Report.objects.create(
            user_id=student_obj,
            course_id=course_obj,
            report_text=report_text
        )

        messages.success(request, "Отчет успешно сохранен и добавлен в общую базу.")

    return redirect("report_list")


def report_delete_view(request, report_id):
    current_role = str(request.session.get('role', '')).strip().lower()
    if current_role not in ['teacher', 'преподаватель']:
        messages.error(request, "У вас нет прав на удаление отчетов.")
        return redirect('report_list')

    report_obj = get_object_or_404(Report, id=report_id)
    report_obj.delete()

    messages.success(request, "Отчет успешно удален из базы данных.")
    return redirect('report_list')


def report_list_view(request):
    search_query = request.GET.get("search", "").strip()
    date_query = request.GET.get("date_search", "").strip()

    reports_queryset = Report.objects.select_related("course_id", "user_id").all().order_by("-created_at")

    if search_query:
        reports_queryset = reports_queryset.annotate(
            full_name_1=Concat("user_id__last_name", Value(" "), "user_id__first_name"),
            full_name_2=Concat("user_id__first_name", Value(" "), "user_id__last_name"),
        ).filter(
            Q(report_text__icontains=search_query) |
            Q(user_id__last_name__icontains=search_query) |
            Q(user_id__first_name__icontains=search_query) |
            Q(full_name_1__icontains=search_query) |
            Q(full_name_2__icontains=search_query)
        )

    if date_query:
        reports_queryset = reports_queryset.filter(created_at__date=date_query)

    reports_table = []
    for report in reports_queryset:
        reports_table.append(
            {
                "id": report.id,
                "date": report.created_at.strftime("%Y-%m-%d %H:%M") if report.created_at else "—",
                "text": report.report_text,
                "course_title": report.course_id.course_title if report.course_id else "Курс удален",
                "student_name": f"{report.user_id.last_name} {report.user_id.first_name}" if report.user_id else "Неизвестный пользователь",
                "student_username": report.user_id.username if report.user_id else "",
                "student_id": report.user_id.id,  # <--- Обязательно передайте ID
                "student_avatar": report.user_id.avatar,
            }
        )

    all_students = []
    all_courses = []
    current_role = str(request.session.get('role', '')).strip().lower()

    if current_role in ['teacher', 'преподаватель']:
        all_students = Users.objects.filter(
            role_perm_id__role_id__role_name__in=["Student", "student", "Студент", "студент"]
        ).order_by("last_name")
        all_courses = Course.objects.all().order_by("course_title")

    context = {
        "reports": reports_table,
        "search_query": search_query,
        "date_query": date_query,
        "all_students": all_students,
        "all_courses": all_courses,
    }
    return render(request, "reports.html", context)


def student_detail_view(request, pk):
    student = get_object_or_404(Users, id=pk)
    enrolled_courses = Enrollment.objects.filter(user_id=student).select_related("course_id")
    courses_list = [emp.course_id for emp in enrolled_courses]

    context = {
        "student": student,
        "enrolled_courses": courses_list,
    }
    return render(request, "student_detail.html", context)


def student_list_view(request):
    search_query = request.GET.get("search", "").strip()
    sort_filter = request.GET.get("sort", "none")

    # Добавляем prefetch_related или просто обращаемся к полям пользователя
    students_qs = Users.objects.filter(
        role_perm_id__role_id__role_name__in=["Student", "student", "Студент", "студент"]
    ).order_by("last_name", "first_name")

    if search_query:
        students_qs = students_qs.annotate(
            full_name_1=Concat("last_name", Value(" "), "first_name"),
            full_name_2=Concat("first_name", Value(" "), "last_name"),
        ).filter(
            Q(last_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(full_name_1__icontains=search_query) |
            Q(full_name_2__icontains=search_query)
        )

    students_table = []

    for student in students_qs:
        enrollments = Enrollment.objects.filter(user_id=student).select_related("course_id")

        courses_list = []
        all_progresses = []

        if enrollments.exists():
            for emp in enrollments:
                if emp.course_id:
                    courses_list.append(emp.course_id.course_title)

                    # Получаем прогресс
                    progress_obj = Progress.objects.filter(
                        user_id=student, course_id=emp.course_id
                    ).first()

                    prog_val = int(
                        progress_obj.progress_percent) if progress_obj and progress_obj.progress_percent else 0
                    all_progresses.append(prog_val)

            avg_progress = round(sum(all_progresses) / len(all_progresses)) if all_progresses else 0
            courses_str = ", ".join(courses_list)
        else:
            courses_str = "Не зачислен"
            avg_progress = 0

        # Добавляем студента в таблицу со всеми нужными полями, включая аватар
        students_table.append({
            "student_id": student.id,
            "full_name": f"{student.last_name} {student.first_name}",
            "course_title": courses_str,
            "courses_badge_list": courses_list,
            "email": f"{student.username}@example.com",
            "progress": avg_progress,
            "avatar": student.avatar,  # <--- ЭТА СТРОКА ВЕРНЕТ АВАТАР В ШАБЛОН
        })

    # Сортировка
    if sort_filter == "high":
        students_table.sort(key=lambda x: x["progress"], reverse=True)
    elif sort_filter == "low":
        students_table.sort(key=lambda x: x["progress"], reverse=False)

    context = {
        "students": students_table,
        "search_query": search_query,
        "sort_filter": sort_filter,
    }
    return render(request, "students.html", context)

from django.db.models import Prefetch

def teacher_list_view(request):
    search_query = request.GET.get("search", "").strip()

    # Оптимизация: предзагружаем все курсы преподавателей одним запросом
    teachers = Users.objects.filter(
        role_perm_id__role_id__role_name__in=["Teacher", "teacher", "Преподаватель", "преподаватель"]
    ).prefetch_related(
        Prefetch('course_set', queryset=Course.objects.all(), to_attr='authored_courses')
    )

    if search_query:
        teachers = teachers.annotate(
            full_name_1=Concat("last_name", Value(" "), "first_name"),
            full_name_2=Concat("first_name", Value(" "), "last_name"),
        ).filter(
            Q(last_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(full_name_1__icontains=search_query) |
            Q(full_name_2__icontains=search_query)
        )
    else:
        teachers = teachers.order_by("last_name", "first_name")

    teachers_table = []
    for teacher in teachers:
        # Используем предзагруженные курсы через атрибут to_attr
        courses_titles = [course.course_title for course in teacher.authored_courses]

        teachers_table.append(
            {
                "id": teacher.id,
                "full_name": f"{teacher.last_name} {teacher.first_name}",
                "username": teacher.username,
                "email": f"{teacher.username}@example.com",
                "courses": ", ".join(courses_titles) if courses_titles else "Нет курсов",
                "avatar": teacher.avatar,  # <--- Добавили аватарку
            }
        )

    context = {
        "teachers": teachers_table,
        "search_query": search_query,
    }
    return render(request, "teachers.html", context)


def toggle_status_view(request, pk):
    current_role = str(request.session.get('role', '')).strip().lower()

    if request.method == "POST" and current_role in ['student', 'студент']:
        user_obj = get_object_or_404(Users, id=request.session.get('user_id'))
        course_obj = get_object_or_404(Course, id=pk)

        item_type = request.POST.get('item_type')
        item_id = request.POST.get('item_id')

        filter_kwargs = {'user_id': user_obj, 'course_id': course_obj}
        filter_kwargs[f"{item_type}_id"] = item_id

        status_obj, created = UserContentStatus.objects.get_or_create(**filter_kwargs)
        if not created:
            status_obj.is_completed = not status_obj.is_completed
            status_obj.save()
        else:
            status_obj.is_completed = True
            status_obj.save()

        total_items = (
                Lecture.objects.filter(course_id=course_obj).count() +
                Exercise.objects.filter(course_id=course_obj).count() +
                Quiz.objects.filter(course_id=course_obj).count()
        )

        completed_items = UserContentStatus.objects.filter(
            user_id=user_obj, course_id=course_obj, is_completed=True
        ).count()

        progress_percent = int((completed_items / total_items) * 100) if total_items > 0 else 0

        progress_obj, _ = Progress.objects.get_or_create(user_id=user_obj, course_id=course_obj)
        progress_obj.progress_percent = str(progress_percent)
        progress_obj.save()

    return redirect('course_detail', pk=pk)


from django.shortcuts import render, get_object_or_404, redirect


def profile_view(request, user_id=None):
    target_id = user_id if user_id else request.session.get('user_id')
    profile_user = get_object_or_404(Users, id=target_id)

    # ОБРАБОТКА РЕДАКТИРОВАНИЯ (POST)
    if request.method == 'POST' and request.session.get('user_id') == profile_user.id:
        profile_user.first_name = request.POST.get('first_name', profile_user.first_name)
        profile_user.last_name = request.POST.get('last_name', profile_user.last_name)
        profile_user.bio = request.POST.get('bio', profile_user.bio)

        # Обработка аватарки
        if request.FILES.get('avatar'):
            profile_user.avatar = request.FILES['avatar']

        profile_user.save()
        return redirect('profile')  # Перезагружаем страницу после сохранения

    # --- ЛОГИКА ОТОБРАЖЕНИЯ (ОСТАЕТСЯ КАК БЫЛА) ---
    role_name = profile_user.role_perm_id.role_id.role_name if profile_user.role_perm_id else ""
    is_teacher = role_name.lower() in ['teacher', 'преподаватель']

    if is_teacher:
        courses = Course.objects.filter(user_id=profile_user)
        enrolled_courses, completed_exercises = [], []
    else:
        enrolled_courses = Enrollment.objects.filter(user_id=profile_user).select_related('course_id')
        completed_exercises = UserContentStatus.objects.filter(
            user_id=profile_user, is_completed=True, exercise__isnull=False
        ).select_related('exercise', 'course_id')
        courses = []

    context = {
        'profile_user': profile_user,
        'role': role_name,
        'is_teacher': is_teacher,
        'enrolled_courses': enrolled_courses,
        'courses': courses,
        'completed_exercises': completed_exercises,
    }
    return render(request, 'profile.html', context)