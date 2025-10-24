from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Department, StudentID, Student, Subject, SubjectMarks, Attendance



class AttendanceInline(admin.TabularInline):
    """Inline for managing attendance records directly within the Student admin."""
    model = Attendance
    extra = 1



@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("department",)

@admin.register(StudentID)
class StudentIDAdmin(admin.ModelAdmin):
    list_display = ("student_id",)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("subject_name",)

@admin.register(SubjectMarks)
class SubjectMarksAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "marks")
    list_filter = ("subject", "student")
    search_fields = ("student__student_name", "subject__subject_name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    
    list_display = ("student_name", "get_student_id", "student_email", "department")
    search_fields = ("student_name", "student_id__student_id", "student_email")
    list_filter = ("department",)

    
    def get_student_id(self, obj):
        return obj.student_id.student_id
    get_student_id.admin_order_field = 'student_id__student_id'
    get_student_id.short_description = 'Student ID'

    
    inlines = [AttendanceInline]

    
    actions = ['export_as_csv']

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        
        field_names = ['student_name', 'student_id', 'department', 'student_email', 'student_age']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=students_export.csv'
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = [
                getattr(obj, 'student_name'), 
                obj.student_id.student_id,
                obj.department.department, 
                getattr(obj, 'student_email'),
                getattr(obj, 'student_age'),
            ]
            writer.writerow(row)

        return response
    
    export_as_csv.short_description = "Export Selected Students (CSV)"