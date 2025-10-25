# students/models.py

from django.db import models
from django.contrib.auth.models import User 
import datetime
USER_ROLES = (
    ('staff', 'Staff/Admin'),
    ('student', 'Student'),
    ('parent', 'Parent'),
)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='student')
    
    # Link to the Student model if the role is 'student'
    student = models.OneToOneField('Student', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='user_profile')

    # Link to a Student model if the role is 'parent'
    # (A parent typically has one primary student account in a school system)
    related_student = models.ForeignKey('Student', on_delete=models.SET_NULL, 
                                        null=True, blank=True, related_name='parent_profiles')

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'

class Department(models.Model):
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.department

    class Meta:
        ordering = ['department']


class StudentID(models.Model):   
    student_id = models.CharField(max_length=100, unique=True) # e.g., STU-1234

    def __str__(self):
        return self.student_id

class Subject(models.Model):
    subject_name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.subject_name


class Student(models.Model):   
    department = models.ForeignKey(Department, related_name="depart", on_delete=models.CASCADE)
    student_id = models.OneToOneField(StudentID, related_name="studentid", on_delete=models.CASCADE)
    student_name = models.CharField(max_length=100)
    student_email = models.EmailField(unique=True)
    student_age = models.IntegerField(default=18)
    student_address = models.TextField()

    def __str__(self):
        return self.student_name

    class Meta:
        ordering = ['student_name']
        verbose_name = "Student"

class SubjectMarks(models.Model):
    student = models.ForeignKey(Student, related_name="studentmarks", on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name="subjectmarks", on_delete=models.CASCADE)
    marks = models.IntegerField()

    def __str__(self):
        return f'{self.student.student_name} - {self.subject.subject_name} ({self.marks})'

    class Meta:
        unique_together = ['student', 'subject']

# students/models.py (Add new model)

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    is_present = models.BooleanField(default=False)

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f'{self.student.student_name} - {self.date} ({status})'

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date']



FEE_STATUS = (
    ('paid', 'Paid'),
    ('pending', 'Pending'),
    ('late', 'Late'),
)

class FeeRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees')
    due_date = models.DateField(default=datetime.date.today)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=FEE_STATUS, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f'{self.student.student_name} - {self.amount_due} ({self.status})'        