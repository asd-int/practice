from django.urls import path
from my_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('courses/', views.course_list_view, name='course_list'),
    path('courses/add/', views.course_add_view, name='course_add'),
    path('students/', views.student_list_view, name='student_list'),
    path('students/<int:pk>/', views.student_detail_view, name='student_detail'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('course/<int:pk>/exercise/<int:exercise_id>/submit/', views.submit_answer_view, name='submit_answer'),
    path('teachers/', views.teacher_list_view, name='teacher_list'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/', views.profile_view, name='profile'),


    path('profile/<int:user_id>/', views.profile_view, name='profile_detail'),
    path('course/<int:pk>/', views.course_detail_view, name='course_detail'),
    path('reports/add/', views.report_add_view, name='report_add'),
    path('reports/delete/<int:report_id>/', views.report_delete_view, name='report_delete'),
    path('reports/', views.report_list_view, name='report_list'),
    path('course/<int:pk>/toggle-status/', views.toggle_status_view, name='toggle_status'),
    path('course/<int:pk>/delete/<str:content_type>/<int:content_id>/', views.delete_content_view, name='delete_content'),
    path('courses/<int:pk>/add-content/', views.add_content_view, name='add_content'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)