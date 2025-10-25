# sms_project/urls.py

from django.contrib import admin
from django.urls import path
from students.views import (
    login_page, register, logout_page, student_report, student_profile, home_page, student_leaderboard, subject_analytics
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin URL
    path('admin/', admin.site.urls),

    # Authentication URLs
    path('login/', login_page, name="login"),
    path('logout/', logout_page, name="logout"),
    path('register/', register, name="register"),

    # Student Management URLs
   path('', home_page, name="home"), # Root URL hits the home_page function
    path('students/', student_report, name="student_report"),
    path('students/', student_report, name="student_report"),
    path('leaderboard/', student_leaderboard, name="student_leaderboard"),
    path('analytics/subjects/', subject_analytics, name="subject_analytics"), # 👈 NEW PATH
    path('student/profile/<str:student_id>/', student_profile, name="student_profile"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)