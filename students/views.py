# students/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models import Avg, Max, Min, Count # Import new aggregators
from .models import Department, Student, SubjectMarks, StudentID, Subject , Attendance , models


# --- Authentication Views ---

def register(request):
    if request.method == "POST":
        # ... (Existing register logic) ...
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('/register/')

        user = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        user.set_password(password)
        user.save()

        messages.success(request, "Account created successfully! Please login.")
        return redirect('/login/')

    return render(request, 'register.html')


def login_page(request):
    if request.method == "POST":
        # ... (Existing login logic) ...
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, 'Invalid Username or Password.')
            return redirect('/login/')
        else:
            login(request, user)
            return redirect('/students/') # Redirect to the main student page

    return render(request, "login.html")


def logout_page(request):
    logout(request)
    return redirect('/login/')

# --- Student Management Views ---

@login_required
def student_report(request):
    student_list = Student.objects.all().select_related('department', 'student_id')
    
    # Unique Feature 1: Search Functionality
    search_query = request.GET.get('search')
    if search_query:
        # Search by student name or student ID
        student_list = student_list.filter(student_name__icontains=search_query) | \
                       student_list.filter(student_id__student_id__icontains=search_query)

    # Pagination
    paginator = Paginator(student_list, 10) 
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "search_query": search_query
    }
    return render(request, "students.html", context)


@login_required
def see_marks(request, student_id):
    # Retrieve marks and student object
    queryset = SubjectMarks.objects.filter(student__student_id__student_id=student_id).select_related('subject')
    student = get_object_or_404(Student, student_id__student_id=student_id)
    
    # Calculate Total Marks
    total_marks = queryset.aggregate(total=Sum('marks'))['total'] or 0

    # Calculate Rank (Unique Feature 2)
    all_totals = (
        SubjectMarks.objects.values('student__student_id__student_id', 'student__student_name')
        .annotate(total=Sum('marks'))
        .order_by('-total')
    )

    rank = None
    for idx, s in enumerate(all_totals, start=1):
        if s['student__student_id__student_id'] == student_id:
            rank = idx
            break

    return render(request, "see_marks.html", {
        "queryset": queryset,
        "total_marks": total_marks,
        "rank": rank,
        "student": student,
    })

# students/views.py (Add this new view)

@login_required
def student_profile(request, student_id):
    """
    Shows a comprehensive profile page for a single student.
    """
    # Use the Student ID string to fetch the Student object
    student = get_object_or_404(Student, student_id__student_id=student_id)
    
    # Existing marks data
    marks_queryset = SubjectMarks.objects.filter(student=student).select_related('subject')

    # Calculate Total Marks (for display)
    total_marks = marks_queryset.aggregate(total=Sum('marks'))['total'] or 0

    # TODO: Fetch Attendance data here once the model is created

    context = {
        'student': student,
        'marks_queryset': marks_queryset,
        'total_marks': total_marks,
        # 'attendance_data': attendance_data, # Add later
    }
    return render(request, 'student_profile.html', context)


def home_page(request):
    """
    Renders the public landing page. 
    Redirects authenticated users to the student report.
    """
    if request.user.is_authenticated:
        # If logged in, send them straight to the main report
        return redirect('student_report')
    
    # If anonymous, show the public landing page (which has Login/Register links)
    return render(request, 'home.html')

# students/views.py (Update student_profile view)

@login_required
def student_profile(request, student_id):
    student = get_object_or_404(Student, student_id__student_id=student_id)
    marks_queryset = SubjectMarks.objects.filter(student=student).select_related('subject')
    total_marks = marks_queryset.aggregate(total=Sum('marks'))['total'] or 0

    # NEW: Fetch Attendance Data
    attendance_data = Attendance.objects.filter(student=student).order_by('-date')
    
    # Calculate Attendance Percentage
    total_days = attendance_data.count()
    present_days = attendance_data.filter(is_present=True).count()
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    context = {
        'student': student,
        'marks_queryset': marks_queryset,
        'total_marks': total_marks,
        'attendance_data': attendance_data, # 👈 ADDED
        'attendance_percentage': round(attendance_percentage, 2), # 👈 ADDED
    }
    return render(request, 'student_profile.html', context)


# students/views.py (Add new leaderboard view)

@login_required
def student_leaderboard(request):
    """
    Calculates overall performance and ranks all students.
    """
    # 1. Calculate totals for all students
    all_students_totals = (
        SubjectMarks.objects.values(
            'student__student_id__student_id',
            'student__student_name',
            'student__department__department'
        )
        .annotate(
            total_marks=Sum('marks'),
            subject_count=models.Count('subject') # Need Count to calculate percentage
        )
        .order_by('-total_marks')
    )

    # 2. Calculate percentage and assign rank
    leaderboard = []
    max_total_marks = Subject.objects.count() * 100 # Assuming max 100 marks per subject
    
    for idx, data in enumerate(all_students_totals, 1):
        total = data['total_marks']
        count = data['subject_count']
        
        # Calculate overall percentage
        percentage = (total / max_total_marks * 100) if max_total_marks > 0 else 0
        
        leaderboard.append({
            'rank': idx,
            'student_id': data['student__student_id__student_id'],
            'student_name': data['student__student_name'],
            'department': data['student__department__department'],
            'total_marks': total,
            'percentage': round(percentage, 2),
        })

    return render(request, 'leaderboard.html', {'leaderboard': leaderboard})

@login_required
def subject_analytics(request):
    """
    Provides statistics (avg, highest, lowest, fail rate) per subject.
    """
    all_subjects = Subject.objects.all()
    
    analytics = []
    
    for subject in all_subjects:
        # Aggregate performance data for the current subject
        stats = SubjectMarks.objects.filter(subject=subject).aggregate(
            avg_marks=Avg('marks'),
            max_marks=Max('marks'),
            min_marks=Min('marks'),
            total_count=Count('marks')
        )
        
        # Calculate Fail Count (marks < 35)
        fail_count = SubjectMarks.objects.filter(subject=subject, marks__lt=35).count()
        
        analytics.append({
            'subject_name': subject.subject_name,
            'avg_marks': round(stats['avg_marks'], 2) if stats['avg_marks'] else 0,
            'max_marks': stats['max_marks'] or 0,
            'min_marks': stats['min_marks'] or 0,
            'total_students': stats['total_count'] or 0,
            'fail_count': fail_count,
            'pass_rate': round(((stats['total_count'] - fail_count) / stats['total_count'] * 100), 2) if stats['total_count'] > 0 else 0
        })

    return render(request, 'subject_analytics.html', {'analytics': analytics})

# --- Seeding Utilities (Keep separate for clean views) ---
from faker import Faker
import random

fake = Faker()

def seed_subjects():
    subjects = ["Data Sturctures and Algorithm", "Database Management System", "Object Oriented Programming", "Operating Systems", "Computer Networks", "Software Engineering"]
    for sub in subjects:
        Subject.objects.get_or_create(subject_name=sub)
    print("✅ Technical Subjects created successfully.")    

def seed_db(n=10) -> None:
    departments_objs = Department.objects.all()

    if not departments_objs.exists():
        print("⚠️ No departments found. Please add departments via /admin/ before seeding.")
        return

    for i in range(n):
        try:
            department = random.choice(departments_objs)
            student_id_str = f"STU-{random.randint(1000, 9999)}"
            while StudentID.objects.filter(student_id=student_id_str).exists():
                student_id_str = f"STU-{random.randint(1000, 9999)}"

            student_id_obj = StudentID.objects.create(student_id=student_id_str)
            
            Student.objects.create(
                department=department,
                student_id=student_id_obj,
                student_name=fake.name(),
                student_email=fake.unique.email(),
                student_age=random.randint(18, 25),
                student_address=fake.address(),
            )

        except Exception as e:
            print(f" Error creating student {i+1}: {e}")

def create_subject_marks(n=None):
    try:
        student_objs = Student.objects.all()
        if n:
            student_objs = student_objs[:n]

        subjects = Subject.objects.all()

        for student in student_objs:
            for subject in subjects:
                # Ensures marks are not duplicated for a student-subject pair
                SubjectMarks.objects.get_or_create(
                    subject=subject,
                    student=student,
                    defaults={'marks': random.randint(0, 100)}
                )
    except Exception as e:
        print(f" Error creating subject marks: {e}")