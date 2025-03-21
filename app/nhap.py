from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib.auth import update_session_auth_hash
from . import models
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import pandas as pd
from django.db import transaction





@login_required
def import_csv(request):
    if request.method == "POST" and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        # Đọc dữ liệu từ file CSV
        data = pd.read_csv(csv_file)

        # # Kiểm tra các cột cần thiết
        # required_columns = ["Mã ngành", "Tên ngành", "Lớp", "Mã sinh viên", "Họ và tên lót", "Tên"]
        # if not all(col in data.columns for col in required_columns):
        #     return redirect('import_student')

        # Chuẩn bị dữ liệu
        departments = []
        students = []
        for _, row in data.iterrows():
            department_code = row["Mã ngành"]
            department_name = row["Tên ngành"]
            student_code = row["Mã sinh viên"]
            last_name = row["Họ và tên lót"]
            first_name = row["Tên"]

            # # Bỏ qua các dòng thiếu dữ liệu bắt buộc
            # if pd.isna(department_code) or pd.isna(department_name) or pd.isna(student_code):
            #     continue

            # Thêm ngành học (Sử dụng update_or_create)
            department, _ = models.Department.objects.update_or_create(
                department_code=str(department_code).strip(),
                defaults={
                    "name": str(department_name).strip()
                }
            )

            # Ghép họ và tên
            full_name = f"{str(last_name).strip()} {str(first_name).strip()}"   

            # Thêm sinh viên vào danh sách
            students.append(
                {
                    "student_code": str(student_code).strip(),
                    "name": full_name,
                    "department_code": str(department_code).strip(),
                }
            )
            # print(students)

        # Thêm ngành học (Sử dụng bulk_create)
        existing_departments = models.Department.objects.all()
        existing_department_codes = set(existing_departments.values_list('department_code', flat=True))

        new_departments = [d for d in departments if d.department_code not in existing_department_codes]
        models.Department.objects.bulk_create(new_departments)

        # Thêm sinh viên (Sử dụng update_or_create)
        with transaction.atomic():
            for student in students:
                department = models.Department.objects.filter(department_code=student["department_code"]).first()
                if not department:
                    print(f"Skipping student: {student['name']} (Department not found for code: {student['department_code']})")
                    continue

                # Tạo user hoặc cập nhật thông tin
                username = student["student_code"]
                email = f"{username}@due.udn.vn"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "password": make_password("12345"),
                    }
                )

                # Tạo hoặc cập nhật sinh viên
                student_obj, created = models.Student.objects.get_or_create(
                    student_code=student["student_code"],
                    defaults={
                        "name": student["name"],
                        "user": user,
                        "department": department,
                    }
                )
                if created:
                    print()
                

        return redirect('import_student')

    return render(request, 'import_student_data.html')

