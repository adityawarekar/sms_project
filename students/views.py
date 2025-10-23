# students/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from .models import Department, Student, SubjectMarks, StudentID, Subject

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

# --- Seeding Utilities (Keep separate for clean views) ---
from faker import Faker
import random

fake = Faker()

def seed_subjects():
    subjects = ["Maths", "Physics", "Chemistry", "Biology", "English", "CS Theory"]
    for sub in subjects:
        Subject.objects.get_or_create(subject_name=sub)
    print("✅ Subjects created successfully.")

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