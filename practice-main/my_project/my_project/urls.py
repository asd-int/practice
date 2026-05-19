"""
URL configuration for my_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""





from django.urls import path
from my_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Экран: Дашборд
    path('', views.dashboard_view, name='dashboard'),

    # 2. Экран: Список курсов + URL для обработки добавления
    path('courses/', views.course_list_view, name='course_list'),
    path('courses/add/', views.course_add_view, name='course_add'),

    # 3. Экран: Список студентов + URL для обработки добавления
    path('students/', views.student_list_view, name='student_list'),
    path('students/add/', views.student_add_view, name='student_add'),

    # 4. Экран: Детальный профиль конкретного студента
    path('students/<int:pk>/', views.student_detail_view, name='student_detail'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Детали курса (доступно всем залогиненным)
    path('course/<int:pk>/', views.course_detail_view, name='course_detail'),
    path('course/<int:pk>/toggle-status/', views.toggle_status_view, name='toggle_status'),

    path('course/<int:pk>/delete/<str:content_type>/<int:content_id>/', views.delete_content_view, name='delete_content'),
    # Обработчик добавления лекций/заданий/тестов внутри курса
    path('courses/<int:pk>/add-content/', views.add_content_view, name='add_content'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)