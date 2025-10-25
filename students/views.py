# students/views.py (COMPLETELY UPDATED FOR RBAC, FEES, and DASHBOARDS)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Avg, Max, Min, Count, Q
from django.http import JsonResponse

# 🚨 CORRECTED IMPORTS: Ensure all necessary models are imported
from .models import Department, Student, SubjectMarks, StudentID, Subject, Attendance, Profile, FeeRecord

import datetime # Required for FeeRecord default
import random # For seeding
from faker import Faker
fake = Faker()


# -------------------------------------------------------------------
# --- AUTHENTICATION & HOME VIEWS ---
# -------------------------------------------------------------------

def register(request):
    # ... (Existing register logic) ...
    if request.method == "POST":
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

        # NOTE: A profile MUST be created in admin for the new user to function.
        messages.success(request, "Account created successfully! Please contact admin to assign a role and profile before login.")
        return redirect('/login/')

    return render(request, 'register.html')


def login_page(request):
    # 🚨 FIX: Consolidating the duplicate login_page functions.
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            
            # --- NEW: ROLE-BASED REDIRECTION ---
            profile = Profile.objects.filter(user=user).first()
            
            if not profile:
                # If no profile, they can't access any dashboard
                messages.error(request, 'No profile assigned. Please contact admin.')
                logout(request)
                return redirect('/login/')
            
            if profile.role == 'staff':
                return redirect('staff_dashboard')
            elif profile.role == 'student':
                return redirect('student_dashboard')
            elif profile.role == 'parent':
                return redirect('parent_dashboard')
            
        else:
            messages.error(request, 'Invalid Username or Password.')
            return redirect('/login/')

    return render(request, "login.html")


def logout_page(request):
    logout(request)
    return redirect('home') # Redirect to the home page


def home_page(request):
    """
    Renders the public landing page. Redirects authenticated users based on role 
    or renders the dashboard if not logged in.
    """
    if request.user.is_authenticated:
        # Check profile for role-based redirection 
        # (This is a cleaner way to ensure they land on their correct dashboard 
        # if they type the root URL after logging in)
        profile = request.user.profile
        if profile.role == 'staff':
            return redirect('staff_dashboard')
        elif profile.role == 'student':
            return redirect('student_dashboard')
        elif profile.role == 'parent':
            return redirect('parent_dashboard')
        
        # Fallback for users with profiles but no recognized role (shouldn't happen)
        return redirect('student_report') 
        
    # If not authenticated, show the public landing page (home.html)
    return render(request, 'home.html')


# -------------------------------------------------------------------
# --- ROLE-BASED DASHBOARDS ---
# -------------------------------------------------------------------

@login_required
def student_dashboard(request):
    """Shows a comprehensive personal dashboard for the logged-in student."""
    if request.user.profile.role != 'student' or not request.user.profile.student:
        messages.error(request, "Access denied or Student profile not linked.")
        logout(request)
        return redirect('home')

    student = request.user.profile.student
    
    # --- ACADEMIC DATA ---
    marks_queryset = SubjectMarks.objects.filter(student=student)
    total_marks_possible = Subject.objects.count() * 100
    
    total_marks = marks_queryset.aggregate(total=Sum('marks'))['total'] or 0
    percentage = round((total_marks / total_marks_possible * 100), 2) if total_marks_possible > 0 else 0
    
    # --- ATTENDANCE DATA ---
    attendance_data = Attendance.objects.filter(student=student)
    total_days = attendance_data.count()
    present_days = attendance_data.filter(is_present=True).count()
    attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0

    # --- FEE DATA ---
    fee_records = FeeRecord.objects.filter(student=student).order_by('-due_date')
    pending_fees = fee_records.filter(status='pending').aggregate(total=Sum('amount_due'))['total'] or 0

    context = {
        'student': student,
        'percentage': percentage,
        'attendance_percentage': attendance_percentage,
        'total_subjects': Subject.objects.count(),
        'total_marks': total_marks,
        'fee_records': fee_records[:5], # Show only 5 recent records
        'pending_fees': pending_fees,
    }
    return render(request, 'dashboards/student_dashboard.html', context)


@login_required
def parent_dashboard(request):
    """Shows a summary dashboard for the parent's linked student."""
    if request.user.profile.role != 'parent' or not request.user.profile.related_student:
        messages.error(request, "Access denied or Parent profile not linked to a student.")
        logout(request)
        return redirect('home')
        
    student = request.user.profile.related_student # The student associated with the parent
    
    # --- ACADEMIC DATA (Child) ---
    marks_queryset = SubjectMarks.objects.filter(student=student)
    total_marks_possible = Subject.objects.count() * 100
    total_marks = marks_queryset.aggregate(total=Sum('marks'))['total'] or 0
    percentage = round((total_marks / total_marks_possible * 100), 2) if total_marks_possible > 0 else 0

    # --- ATTENDANCE DATA (Child) ---
    attendance_data = Attendance.objects.filter(student=student)
    total_days = attendance_data.count()
    present_days = attendance_data.filter(is_present=True).count()
    attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0

    # --- FEE DATA (Child) ---
    fee_records = FeeRecord.objects.filter(student=student).order_by('-due_date')
    pending_fees = fee_records.filter(status='pending').aggregate(total=Sum('amount_due'))['total'] or 0
    
    context = {
        'student': student,
        'percentage': percentage,
        'attendance_percentage': attendance_percentage,
        'pending_fees': pending_fees,
        'fee_records': fee_records[:3],
    }
    return render(request, 'dashboards/parent_dashboard.html', context)


@login_required
def staff_dashboard(request):
    """A simple entry point for staff to access admin tools and reports."""
    if request.user.profile.role != 'staff':
        messages.error(request, "Access denied. Only Staff can view this dashboard.")
        logout(request)
        return redirect('home')

    # Quick overview stats for the staff dashboard
    total_students = Student.objects.count()
    total_departments = Department.objects.count()
    # Use Count from SubjectMarks to avoid error if no marks exist
    avg_performance = SubjectMarks.objects.aggregate(avg=Avg('marks'))['avg']
    pending_fee_count = FeeRecord.objects.filter(status='pending').count()
    
    context = {
        'total_students': total_students,
        'total_departments': total_departments,
        'avg_performance': round(avg_performance, 2) if avg_performance else 0,
        'pending_fee_count': pending_fee_count,
    }
    return render(request, 'dashboards/staff_dashboard.html', context)


# -------------------------------------------------------------------
# --- CORE STUDENT REPORTS (Mainly Staff/Admin) ---
# -------------------------------------------------------------------

@login_required
def student_report(request):
    # 🚨 SECURITY NOTE: Ideally, limit this view to Staff/Admin role only
    if request.user.profile.role not in ['staff', 'admin']:
        messages.error(request, "You do not have permission to view the full student list.")
        return redirect('home')

    student_list = Student.objects.all().select_related('department', 'student_id')
    
    # ... (Search and Pagination logic remains the same) ...
    search_query = request.GET.get('search')
    if search_query:
        student_list = student_list.filter(student_name__icontains=search_query) | \
                        student_list.filter(student_id__student_id__icontains=search_query)

    paginator = Paginator(student_list, 10) 
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "search_query": search_query
    }
    return render(request, "students.html", context)


@login_required
def student_profile(request, student_id):
    """
    Shows a comprehensive profile page for a single student (viewable by Staff/Parent).
    """
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
        'attendance_data': attendance_data,
        'attendance_percentage': round(attendance_percentage, 2),
    }
    # Uses the student_profile.html template
    return render(request, 'student_profile.html', context)


@login_required
def student_leaderboard(request):
    """Calculates overall performance and ranks all students."""
    all_students_totals = (
        SubjectMarks.objects.values(
            'student__student_id__student_id',
            'student__student_name',
            'student__department__department'
        )
        .annotate(
            total_marks=Sum('marks'),
            subject_count=Count('subject')
        )
        .order_by('-total_marks')
    )

    leaderboard = []
    max_total_marks = Subject.objects.count() * 100 
    
    for idx, data in enumerate(all_students_totals, 1):
        total = data['total_marks']
        # count = data['subject_count'] # Not used directly in loop, but useful for verification
        
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
    """Provides statistics (avg, highest, lowest, fail rate) per subject."""
    all_subjects = Subject.objects.all()
    
    analytics = []
    
    for subject in all_subjects:
        stats = SubjectMarks.objects.filter(subject=subject).aggregate(
            avg_marks=Avg('marks'),
            max_marks=Max('marks'),
            min_marks=Min('marks'),
            total_count=Count('marks')
        )
        
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


# -------------------------------------------------------------------
# --- API FOR CHARTS ---
# -------------------------------------------------------------------

@login_required
def get_student_attendance_chart_data(request):
    """Generates JSON data for the currently logged-in student's attendance pie chart."""
    # Ensure the user is a student and linked
    if not request.user.profile.student or request.user.profile.role != 'student':
        return JsonResponse({'error': 'Unauthorized or Student not linked'}, status=403)
        
    student = request.user.profile.student
    
    attendance_stats = student.attendances.aggregate(
        present_count=Count('pk', filter=Q(is_present=True)),
        absent_count=Count('pk', filter=Q(is_present=False)),
    )
    
    data = {
        'labels': ['Present', 'Absent'],
        'counts': [attendance_stats['present_count'], attendance_stats['absent_count']],
    }
    return JsonResponse(data)


# -------------------------------------------------------------------
# --- SEEDING UTILITIES (Keep at the bottom) ---
# -------------------------------------------------------------------

def seed_subjects():
    subjects = ["Data Structures and Algorithm", "Database Management System", "Object Oriented Programming", "Operating Systems", "Computer Networks", "Software Engineering"]
    for sub in subjects:
        Subject.objects.get_or_create(subject_name=sub)
    print("✅ Technical Subjects created successfully.") 
    
# ... (seed_db and create_subject_marks remain the same) ...


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
                SubjectMarks.objects.get_or_create(
                    subject=subject,
                    student=student,
                    defaults={'marks': random.randint(0, 100)}
                )
    except Exception as e:
        print(f" Error creating subject marks: {e}")