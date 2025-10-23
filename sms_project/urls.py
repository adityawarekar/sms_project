# sms_project/urls.py

from django.contrib import admin
from django.urls import path
from students.views import (
    login_page, register, logout_page, student_report, see_marks
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
    path('', student_report, name="student_report"), # Root URL redirects to students
    path('students/', student_report, name="student_report"),
    path('see_marks/<str:student_id>/', see_marks, name="see_marks"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)