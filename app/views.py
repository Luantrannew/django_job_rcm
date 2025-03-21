from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import pandas as pd
from django.db import transaction
import os
from . import models, nlp
from django.db.models import Q, Max
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import traceback


def index (request): 
    template = 'index.html'
    context = {}
    return render(request,template, context)

@login_required(login_url='sign_in')
def student_form(request):
    template = 'student_form.html'

    if request.method == 'POST':
        student_name = request.POST.get('student_name')
        student_code = request.POST.get('student_code')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        study_year = request.POST.get('study_year')

        try:
            # Tạo User với mật khẩu mặc định là '12345'
            user = User.objects.create_user(username=student_code, email=email)
            user.set_password('12345')  # Đặt mật khẩu mặc định
            user.save()

            # Tạo Student và liên kết với User
            student = models.Student.objects.create(
                user=user,
                name=student_name,
                student_code=student_code,
                email=email,
                phone=phone,
                study_year=study_year,
            )

            response_data = {
                'message': 'Đã đăng ký thành công sinh viên mới với mật khẩu mặc định',
                'studentForm': {
                    'name': student.name,
                    'student_code': student.student_code
                }
            }
            return JsonResponse(response_data, status=201)

        except Exception as e:
            return JsonResponse({"message": f"Lỗi: {str(e)}"}, status=400)

    context = {}
    return render(request, template, context)

def sign_in(request):
    if request.method == 'POST':
        student_code = request.POST.get('username')
        password = request.POST.get('password')

        # Sử dụng authenticate của Django
        user = authenticate(request, username=student_code, password=password)
        if user is not None:
            if user.is_staff:  # Nếu là tài khoản admin
                login(request, user)  # Đăng nhập session
                return JsonResponse({"message": "Đăng nhập thành công (Admin)", "status": "success"}, status=200)
            else:  # Nếu là tài khoản thông thường
                try:
                    # Đảm bảo user liên kết với Student
                    student = models.Student.objects.get(user=user)
                    login(request, user)  # Đăng nhập session
                    return JsonResponse({"message": "Đăng nhập thành công", "status": "success"}, status=200)
                except models.Student.DoesNotExist:
                    return JsonResponse({"message": "Tài khoản không được liên kết với sinh viên", "status": "error"}, status=400)
        else:
            return JsonResponse({"message": "Tên đăng nhập hoặc mật khẩu không đúng", "status": "error"}, status=400)

    return render(request, 'sign_in.html')

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required(login_url='sign_in')
def profile(request):
    student = models.Student.objects.filter(user=request.user).first()
    return render(request, 'profile.html', {'student': student})

@login_required(login_url='sign_in')
def update_profile(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student = models.Student.objects.filter(user=request.user).first()
            student.name = data.get('name', student.name)
            student.email = data.get('email', student.email)
            student.phone = data.get('phone', student.phone)
            student.study_year = data.get('study_year', student.study_year)
            student.save()
            return JsonResponse({"success": True, "message": "Thông tin đã được cập nhật thành công!"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Có lỗi xảy ra: {str(e)}"})
    return JsonResponse({"success": False, "message": "Yêu cầu không hợp lệ"})

@login_required(login_url='sign_in')
def change_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            if not request.user.check_password(current_password):
                return JsonResponse({"success": False, "message": "Mật khẩu hiện tại không đúng."})
            
            if new_password != confirm_password:
                return JsonResponse({"success": False, "message": "Mật khẩu mới và xác nhận mật khẩu không khớp."})
            
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Giữ người dùng đăng nhập sau khi đổi mật khẩu
            
            return JsonResponse({"success": True, "message": "Đổi mật khẩu thành công."})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Có lỗi xảy ra: {str(e)}"})
    return JsonResponse({"success": False, "message": "Yêu cầu không hợp lệ"})


@login_required(login_url='sign_in')
def cv_list(request): 
    template = 'cv_list.html'
    # Lấy sinh viên từ user đã đăng nhập
    student = models.Student.objects.filter(user=request.user).first()
    if student:
        CVs = models.CV.objects.filter(student=student)
    else:
        CVs = models.CV.objects.none()
    context = {
        'CVs': CVs
    }
    return render(request, template, context)


def cv_detail(request, pk):
    template = 'cv_detail.html'
    cv = models.CV.objects.filter(pk=pk).last()

    experiences = models.ExperienceinCV.objects.filter(cv=cv).select_related('experience')
    educations = models.EducationinCV.objects.filter(cv=cv).select_related('education')
    skills = models.SkillinCV.objects.filter(cv=cv).select_related('skill')
    projects = models.Project.objects.filter(cv=cv)
    certifications = models.Certification.objects.filter(cv=cv)
    languages = models.LanguageinCV.objects.filter(cv=cv).select_related('language')

    # Use prefetch_related for display names to optimize queries
    social_links = models.SocialLink.objects.filter(cv=cv).prefetch_related('displayname_set') # chúa ngu

    context = {
        'cv': cv,
        'experiences': experiences,
        'educations': educations,
        'skills': skills,
        'projects': projects,
        'certifications': certifications,
        'languages': languages,
        'social_links': social_links,
    }

    return render(request, template, context)

from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from PIL import Image as PILImage
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Đường dẫn tuyệt đối đến font

# FONT_PATH_REGULAR = r"C:\working\job_rcm\job_rcm_code\django\due_job_rcm\app\static\fonts\Nunito-Regular.ttf"
# FONT_PATH_BOLD = r"C:\working\job_rcm\job_rcm_code\django\due_job_rcm\app\static\fonts\Nunito-Bold.ttf"


# # Kiểm tra nếu file font tồn tại trước khi đăng ký (tránh lỗi)
# if os.path.exists(FONT_PATH_REGULAR) and os.path.exists(FONT_PATH_BOLD):
#     pdfmetrics.registerFont(TTFont('Nunito', FONT_PATH_REGULAR))
#     pdfmetrics.registerFont(TTFont('Nunito-Bold', FONT_PATH_BOLD))
# else:
#     raise FileNotFoundError("Font Nunito không tìm thấy. Kiểm tra lại đường dẫn trong static/fonts/")



from django.contrib.staticfiles import finders

# Use finders to get the actual file system path
FONT_PATH_REGULAR = finders.find('fonts/Nunito-Regular.ttf')
FONT_PATH_BOLD = finders.find('fonts/Nunito-Bold.ttf')

# Kiểm tra nếu file font tồn tại trước khi đăng ký
if FONT_PATH_REGULAR and FONT_PATH_BOLD:
    pdfmetrics.registerFont(TTFont('Nunito', FONT_PATH_REGULAR))
    pdfmetrics.registerFont(TTFont('Nunito-Bold', FONT_PATH_BOLD))
else:
    raise FileNotFoundError("Font Nunito không tìm thấy. Kiểm tra lại đường dẫn trong static/fonts/")


def generate_cv_pdf(request, cv_id):
    cv = get_object_or_404(models.CV, pk=cv_id)

    experiences = models.ExperienceinCV.objects.filter(cv=cv).select_related('experience')
    certifications = models.Certification.objects.filter(cv=cv)
    skills = models.SkillinCV.objects.filter(cv=cv).select_related('skill')
    languages = models.LanguageinCV.objects.filter(cv=cv).select_related('language')
    projects = models.Project.objects.filter(cv=cv)
    social_links = models.SocialLink.objects.filter(cv=cv).prefetch_related('displayname_set')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)

    elements = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle("Title", fontSize=24, fontName="Nunito-Bold", textColor=colors.HexColor("#1F3864"), alignment=1, spaceAfter=6)
    subtitle_style = ParagraphStyle("Subtitle", fontSize=10, fontName="Nunito", textColor=colors.black, alignment=1, spaceAfter=10)
    section_style = ParagraphStyle("Section", fontSize=16, fontName="Nunito-Bold", textColor=colors.HexColor("#1F3864"), spaceBefore=15, spaceAfter=8)
    normal_style = ParagraphStyle("Normal", fontSize=11, fontName="Nunito", leading=14)
    job_title_style = ParagraphStyle("JobTitle", fontSize=12, fontName="Nunito-Bold", textColor=colors.black, spaceBefore=8)
    company_style = ParagraphStyle("Company", fontSize=12, fontName="Nunito", textColor=colors.HexColor("#0563C1"))
    date_style = ParagraphStyle("Date", fontSize=11, fontName="Nunito", textColor=colors.gray, alignment=2)
    bullet_style = ParagraphStyle("Bullet", fontSize=11, fontName="Nunito", leading=14, leftIndent=15, firstLineIndent=-10)

    # Profile Section
    if cv.avatar:
        try:
            avatar_path = cv.avatar.path
            with PILImage.open(avatar_path) as img:
                width, height = img.size
                new_size = min(width, height)
                left = (width - new_size) / 2
                top = (height - new_size) / 2
                right = (width + new_size) / 2
                bottom = (height + new_size) / 2
                cropped_img = img.crop((left, top, right, bottom))

                img_buffer = BytesIO()
                cropped_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)

            profile_img = Image(img_buffer, width=100, height=100)
            profile_data = [[profile_img], [Paragraph(cv.student.name, title_style)]]
        except FileNotFoundError:
            profile_data = [[Paragraph(cv.student.name, title_style)]]
    else:
        profile_data = [[Paragraph(cv.student.name, title_style)]]

    # Create a table for profile section with image (if exists) and name centered
    profile_table = Table(profile_data, colWidths=[450])
    profile_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(profile_table)
    elements.append(Spacer(1, 20))


    # Contact information
    elements.append(Paragraph(f"+84-{cv.student.phone}", subtitle_style))
    # elements.append(Spacer(1, 7))
    elements.append(Paragraph(f"{cv.student.email}", subtitle_style))
    
    # 📌 Social Links (Hiển thị tối đa 3 links mỗi hàng, căn giữa)
    if social_links.exists():
        social_texts = []
        
        for link in social_links:
            display_name = link.displayname_set.first().display_name if link.displayname_set.exists() else link.link
            social_texts.append(f"<a href='{link.link}'>{display_name}</a>")

        # Chia social links thành từng hàng (tối đa 3 link trên mỗi hàng)
        row_size = 3
        social_rows = [social_texts[i:i + row_size] for i in range(0, len(social_texts), row_size)]

        # Tạo bảng hiển thị social links
        social_data = [[Paragraph(text, normal_style) for text in row] for row in social_rows]
        social_table = Table(social_data, colWidths=[150] * row_size)  # Định nghĩa độ rộng từng cột

        # Style bảng
        social_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#003366")),
            ('FONTNAME', (0, 0), (-1, -1), "Helvetica-Bold"),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(Spacer(1, 10))
        elements.append(social_table)

    
    # Add a separator line
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=10))
    
    # About Me Section
    if cv.about_me:
        elements.append(Paragraph("About Me", section_style))
        elements.append(Paragraph(cv.about_me, normal_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=0))
    
   # Professional Experience
    if experiences.exists():
        elements.append(Paragraph("Professional Experience", section_style))
        for exp in experiences:
            job = exp.experience
            
            # Create a table for job title and company with better spacing
            job_company_data = [[
                Paragraph(f"{job.role},", job_title_style),
                Paragraph(f"({job.company_name})", company_style)
            ]]
            
            # Adjust column widths to bring elements closer together
            job_table = Table(job_company_data, colWidths=[300, 150])
            job_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                ('BOX', (0, 0), (-1, -1), 0, colors.white),
            ]))
            elements.append(job_table)
            
            # Date formatting (this part is already good)
            date_text = f"{job.start_date.strftime('%d/%m/%Y')} - {job.end_date.strftime('%d/%m/%Y') if job.end_date else 'Present'}"
            elements.append(Paragraph(date_text, date_style))
            
            # Job responsibilities
            for line in job.context.split("\n"):
                if line.strip():
                    elements.append(Paragraph(f"• {line.strip()}", bullet_style))
            
            elements.append(Spacer(1, 10))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0, spaceAfter=0))
    
    # Certifications
    if certifications.exists():
        elements.append(Paragraph("Certifications", section_style))
        for cert in certifications:
            elements.append(Paragraph(f"• {cert.certificate}", bullet_style))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=0))
    
    # Skills (as badges similar to HTML)
    if skills.exists():
        elements.append(Paragraph("Skills", section_style))
        
        # Create a flowable table of skills that wraps
        skill_data = []
        current_row = []
        
        for idx, skill in enumerate(skills):
            current_row.append(Paragraph(f"{skill.skill.skill}", normal_style))
            
            # Create rows with 3 skills each
            if len(current_row) == 3 or idx == len(skills) - 1:
                # Fill empty cells if needed
                while len(current_row) < 3:
                    current_row.append("")
                
                skill_data.append(current_row)
                current_row = []
        
        if skill_data:
            skill_table = Table(skill_data, colWidths=[145, 145, 145])
            skill_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#8182aa")),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.white),
                ('ROUNDEDCORNERS', [5, 5, 5, 5]),
            ]))
            elements.append(skill_table)
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=0))
    
    # Languages
    if languages.exists():
        elements.append(Paragraph("Languages", section_style))
        for lang in languages:
            elements.append(Paragraph(f"<b>{lang.language.language}</b>", normal_style))
            elements.append(Paragraph(f"{lang.language.text}", ParagraphStyle("LangDesc", parent=normal_style, textColor=colors.gray, leftIndent=10)))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=10, spaceAfter=0))
    
    # Projects
    if projects.exists():
        elements.append(Paragraph("Projects", section_style))
        for project in projects:
            elements.append(Paragraph(f"<b>{project.project_name}</b>", job_title_style))
            elements.append(Spacer(1, 10))
            
            for line in project.project_content.split("\n"):
                if line.strip():
                    elements.append(Paragraph(f"• {line.strip()}", bullet_style))
            
            if project.project_link_set.exists():
                elements.append(Paragraph(f"(<a href='{project.project_link_set.first().link}' color='#0563C1'>link</a>)", normal_style))
            
            elements.append(Spacer(1, 10))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{cv.student.name}_CV.pdf"'
    return response




def get_student_info(request, pk):
    try:
        student = models.Student.objects.get(pk=pk)
        data = {
            'name': student.name,
            'student_code': student.student_code,
            'email': student.email,
            'phone': student.phone,
            'study_year': student.study_year
        }
        return JsonResponse(data)
    except models.Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)


@login_required(login_url='sign_in')
def cv_form(request, pk=None):
    template = 'cv_form.html'

    # Lấy thông tin sinh viên và các trường đại học
    student = models.Student.objects.filter(user=request.user).first()
    universitys = models.University.objects.all()
    cv = None

    # Kiểm tra nếu đang chỉnh sửa một CV
    if pk:
        cv = models.CV.objects.filter(pk=pk, student=student).first()

    if request.method == 'POST':
        print(request.POST)
        # Lấy dữ liệu từ form
        name = request.POST.get('cv_name')
        about_me = request.POST.get('about_me')
        avatar = request.FILES.get('avatar')  # Lấy file avatar từ form
        # Kiểm tra giá trị avatar
        print("Avatar Path:",avatar)

        # Nếu là chỉnh sửa CV
        if cv:
            cv.name = name
            cv.about_me = about_me
            if avatar:
                cv.avatar = avatar
            cv.save()
        else:  # Nếu là tạo mới CV
            cv = models.CV.objects.create(
                name=name,
                about_me=about_me,
                student=student,
                avatar=avatar
            )

        # Xử lý Social Links
        social_links = []
        social_link_count = int(request.POST.get('social_link_count', 0))
        for i in range(social_link_count):
            link = request.POST.get(f'social_link_{i}')
            display_name = request.POST.get(f'social_link_{i}_display_name')

            if link:
                social_link_obj = models.SocialLink.objects.create(cv=cv, link=link)
                if display_name:
                    models.Displayname.objects.create(social_link=social_link_obj, display_name=display_name)

        # Xử lý Ngôn ngữ
        language_index = 0
        while True:
            language_name = request.POST.get(f'language_{language_index}_name')
            description = request.POST.get(f'language_{language_index}_description')
            if not language_name:
                break
            language = models.Language.objects.create(language=language_name, text=description)
            models.LanguageinCV.objects.create(cv=cv, language=language)
            language_index += 1

        # Xử lý Chứng chỉ
        certifications = [key for key in request.POST if key.startswith('certification_') and not key.endswith('_count')]
        for cert_key in certifications:
            certificate = request.POST.get(cert_key)
            if certificate:
                models.Certification.objects.create(cv=cv, certificate=certificate)

        # Xử lý Dự án
        project_index = 0
        while True:
            project_name = request.POST.get(f'project_{project_index}_name')
            project_content = request.POST.get(f'project_{project_index}_description')
            project_link = request.POST.get(f'project_{project_index}_link')
            if not project_name:
                break
            project = models.Project.objects.create(
                project_name=project_name,
                project_content=project_content,
                cv=cv
            )
            if project_link:
                models.Project_link.objects.create(project=project, link=project_link)
            project_index += 1

        # Xử lý Học vấn
        education_index = 0
        while True:
            university_pk = request.POST.get(f'education_{education_index}_university')
            if not university_pk:
                break
            degree = request.POST.get(f'education_{education_index}_degree')
            start_year = request.POST.get(f'education_{education_index}_start_year')
            end_year = request.POST.get(f'education_{education_index}_end_year')
            if university_pk.isdigit():
                university = models.University.objects.get(pk=university_pk)
            else:
                university, _ = models.University.objects.get_or_create(university_name=university_pk)
            education = models.Education.objects.create(
                university=university,
                degree=degree,
                start_year=start_year,
                end_year=end_year
            )
            models.EducationinCV.objects.create(cv=cv, education=education)
            education_index += 1

        # Xử lý Kinh nghiệm
        experiences = [key for key in request.POST if key.startswith('experience_') and key.endswith('_company_name')]
        for experience_key in experiences:
            index = experience_key.split('_')[1]
            company_name = request.POST.get(f'experience_{index}_company_name')
            role = request.POST.get(f'experience_{index}_role')
            start_date = request.POST.get(f'experience_{index}_start_date')
            end_date = request.POST.get(f'experience_{index}_end_date')
            context = request.POST.get(f'experience_{index}_context')
            if company_name:
                experience = models.Experience.objects.create(
                    company_name=company_name,
                    role=role,
                    start_date=start_date,
                    end_date=end_date,
                    context=context
                )
                models.ExperienceinCV.objects.create(cv=cv, experience=experience)

        # Xử lý Kỹ năng
        skills = [key for key in request.POST if key.startswith('skill_') and not key.endswith('_count')]
        for skill_key in skills:
            skill_name = request.POST.get(skill_key)
            if skill_name:
                skill, _ = models.Skill.objects.get_or_create(skill=skill_name)
                models.SkillinCV.objects.create(cv=cv, skill=skill)

        messages.success(request, "CV đã được lưu thành công.")
        return redirect('cv_list')

    # Truyền dữ liệu vào context để hiển thị trên form
    context = {
        'cv': cv,
        'student': student,
        'universitys': universitys,
        'social_links': models.SocialLink.objects.filter(cv=cv) if cv else [],
        'projects': models.Project.objects.filter(cv=cv) if cv else [],
        'languages': models.LanguageinCV.objects.filter(cv=cv) if cv else [],
        'certifications': models.Certification.objects.filter(cv=cv) if cv else [],
        'experiences': models.ExperienceinCV.objects.filter(cv=cv) if cv else [],
        'skills': models.SkillinCV.objects.filter(cv=cv) if cv else [],
    }
    return render(request, template, context)



@login_required(login_url='sign_in')
def update_cv(request, pk):
    template = 'cv_form.html'
    
    # Lấy thông tin CV và student
    student = models.Student.objects.filter(user=request.user).first()
    cv = models.CV.objects.filter(pk=pk, student=student).first()

    if not cv:
        return HttpResponse("CV không tồn tại hoặc bạn không có quyền chỉnh sửa.", status=404)

    if request.method == 'POST':
        # Cập nhật thông tin CV
        cv.name = request.POST.get('cv_name', cv.name)
        cv.about_me = request.POST.get('about_me', cv.about_me)
        cv.save()

        # Cập nhật liên kết cá nhân
        models.SocialLink.objects.filter(cv=cv).delete()
        social_link_count = int(request.POST.get('social_link_count', 0))
        for i in range(social_link_count):
            link = request.POST.get(f'social_link_{i}')
            display_name = request.POST.get(f'social_link_{i}_display_name')
            if link:
                social_link_obj = models.SocialLink.objects.create(cv=cv, link=link)
                if display_name:
                    models.Displayname.objects.create(social_link=social_link_obj, display_name=display_name)

        # Cập nhật ngôn ngữ
        models.LanguageinCV.objects.filter(cv=cv).delete()
        language_index = 0
        while True:
            language_name = request.POST.get(f'language_{language_index}_name')
            description = request.POST.get(f'language_{language_index}_description')
            if not language_name:
                break
            language = models.Language.objects.create(language=language_name, text=description)
            models.LanguageinCV.objects.create(cv=cv, language=language)
            language_index += 1

        # Cập nhật chứng chỉ
        models.Certification.objects.filter(cv=cv).delete()
        certifications = [key for key in request.POST if key.startswith('certification_') and not key.endswith('_count')]
        for cert_key in certifications:
            certificate = request.POST.get(cert_key)
            if certificate:
                models.Certification.objects.create(cv=cv, certificate=certificate)

        # Cập nhật dự án
        models.Project.objects.filter(cv=cv).delete()
        project_index = 0
        while True:
            project_name = request.POST.get(f'project_{project_index}_name')
            project_content = request.POST.get(f'project_{project_index}_description')
            project_link = request.POST.get(f'project_{project_index}_link')
            if not project_name:
                break
            project = models.Project.objects.create(
                project_name=project_name,
                project_content=project_content,
                cv=cv
            )
            if project_link:
                models.Project_link.objects.create(project=project, link=project_link)
            project_index += 1

        # Cập nhật học vấn
        models.EducationinCV.objects.filter(cv=cv).delete()
        education_index = 0
        while True:
            university_pk = request.POST.get(f'education_{education_index}_university')
            if not university_pk:
                break
            degree = request.POST.get(f'education_{education_index}_degree')
            start_year = request.POST.get(f'education_{education_index}_start_year')
            end_year = request.POST.get(f'education_{education_index}_end_year')
            if university_pk.isdigit():
                university = models.University.objects.get(pk=university_pk)
            else:
                university, _ = models.University.objects.get_or_create(university_name=university_pk)
            education = models.Education.objects.create(
                university=university,
                degree=degree,
                start_year=start_year,
                end_year=end_year
            )
            models.EducationinCV.objects.create(cv=cv, education=education)
            education_index += 1

        # Cập nhật kinh nghiệm
        models.ExperienceinCV.objects.filter(cv=cv).delete()
        experiences = [key for key in request.POST if key.startswith('experience_') and key.endswith('_company_name')]
        for experience_key in experiences:
            index = experience_key.split('_')[1]
            company_name = request.POST.get(f'experience_{index}_company_name')
            role = request.POST.get(f'experience_{index}_role')
            start_date = request.POST.get(f'experience_{index}_start_date')
            end_date = request.POST.get(f'experience_{index}_end_date')
            context = request.POST.get(f'experience_{index}_context')
            if company_name:
                experience = models.Experience.objects.create(
                    company_name=company_name,
                    role=role,
                    start_date=start_date,
                    end_date=end_date,
                    context=context
                )
                models.ExperienceinCV.objects.create(cv=cv, experience=experience)

        # Cập nhật kỹ năng
        models.SkillinCV.objects.filter(cv=cv).delete()
        skills = [key for key in request.POST if key.startswith('skill_') and not key.endswith('_count')]
        for skill_key in skills:
            skill_name = request.POST.get(skill_key)
            if skill_name:
                skill, _ = models.Skill.objects.get_or_create(skill=skill_name)
                models.SkillinCV.objects.create(cv=cv, skill=skill)

        messages.success(request, "CV đã được cập nhật thành công.")
        return redirect('cv_detail', pk=pk)

    # Dữ liệu để hiển thị form
    social_links = models.SocialLink.objects.filter(cv=cv).prefetch_related('displayname_set')
    languages = models.LanguageinCV.objects.filter(cv=cv).select_related('language')
    certifications = models.Certification.objects.filter(cv=cv)
    projects = models.Project.objects.filter(cv=cv)
    experiences = models.ExperienceinCV.objects.filter(cv=cv).select_related('experience')
    skills = models.SkillinCV.objects.filter(cv=cv).select_related('skill')
    educations = models.EducationinCV.objects.filter(cv=cv).select_related('education')

    context = {
        'cv': cv,
        'student': student,
        'social_links': social_links,
        'languages': languages,
        'certifications': certifications,
        'projects': projects,
        'experiences': experiences,
        'skills': skills,
        'educations': educations,
    }
    return render(request, template, context)


@login_required(login_url='sign_in')
def delete_cv(request, pk):
    # Lấy sinh viên hiện tại
    student = models.Student.objects.filter(user=request.user).first()

    # Tìm CV và kiểm tra quyền sở hữu
    cv_queryset = models.CV.objects.filter(pk=pk, student=student)
    if not cv_queryset.exists():
        messages.error(request, "CV không tồn tại hoặc bạn không có quyền xóa.")
        return redirect('cv_list')

    if request.method == 'POST':
        # Xóa CV
        cv_queryset.first().delete()
        messages.success(request, "CV đã được xóa thành công.")
        return redirect('cv_list')


import csv

@login_required
def import_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            # Kiểm tra định dạng file
            if not csv_file.name.endswith('.csv'):
                return JsonResponse({'status': 'error', 'message': "File không đúng định dạng CSV."})

            try:
                # Đọc file CSV
                decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
                reader = csv.DictReader(decoded_file)

                results = []  # Danh sách lưu kết quả của từng dòng

                for row in reader:
                    try:
                        # Lấy thông tin từ từng dòng và chuyển đổi thành chuỗi
                        department_code = str(row['Mã ngành']).strip()
                        department_name = str(row['Tên ngành']).strip()
                        student_class = str(row['Lớp']).strip()
                        student_code = str(row['Mã sinh viên']).strip()
                        last_name = str(row['Họ và tên lót']).strip()
                        first_name = str(row['Tên']).strip()

                        # Tạo hoặc lấy Department
                        department, _ = models.Department.objects.get_or_create(
                            department_code=department_code,
                            defaults={'name': department_name}
                        )

                        # Tạo User
                        email = f"{student_code}@due.udn.vn"
                        user, created = User.objects.get_or_create(
                            username=student_code,
                            defaults={
                                'email': email,
                                'password': '12345',
                                'first_name': first_name,
                                'last_name': last_name,
                            }
                        )
                        if created:
                            user.set_password('12345')
                            user.save()

                        # Tạo Student
                        models.Student.objects.get_or_create(
                            user=user,
                            defaults={
                                'name': f"{last_name} {first_name}",
                                'student_code': student_code,
                                'email': email,
                                'phone': '',
                                'study_year': student_class,
                                'department': department,
                            }
                        )

                        # Ghi kết quả thành công
                        results.append({
                            'status': 'success',
                            'student_code': student_code,
                            'full_name': f"{last_name} {first_name}",
                            'student_class': student_class,
                            'created': created,
                        })

                    except Exception as e:
                        # Ghi kết quả lỗi
                        results.append({
                            'status': 'error',
                            'student_code': student_code,
                            'full_name': f"{last_name} {first_name}",
                            'student_class': student_class,
                            'error': str(e)
                        })

                # Trả về kết quả của tất cả các dòng
                return JsonResponse({
                    'status': 'complete',
                    'results': results
                })

            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"Có lỗi xảy ra: {str(e)}"})

    return render(request, 'import_student_data.html')







@login_required
def student_management(request):
    students = models.Student.objects.all()
    departments = models.Department.objects.all()

    # Apply filters
    name = request.GET.get('name', '').strip()
    student_code = request.GET.get('student_code', '').strip()
    email = request.GET.get('email', '').strip()
    phone = request.GET.get('phone', '').strip()
    study_year = request.GET.get('study_year', '').strip()
    department_id = request.GET.get('department', '').strip()

    if name:
        students = students.filter(name__icontains=name)
    if student_code:
        students = students.filter(student_code__icontains=student_code)
    if email:
        students = students.filter(email__icontains=email)
    if phone:
        students = students.filter(phone__icontains=phone)
    if study_year:
        students = students.filter(study_year__icontains=study_year)
    if department_id:
        students = students.filter(department_id=department_id)

    context = {
        'students': students,
        'departments': departments,
    }
    return render(request, 'student_management.html', context)



##################################################
##################################################
# Module Job #####################################
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required(login_url='sign_in')
def import_jobs(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            if not csv_file.name.endswith('.csv'):
                return JsonResponse({'status': 'error', 'message': "File không đúng định dạng CSV."})

            try:
                decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
                reader = csv.DictReader(decoded_file)

                results = []
                for row in reader:
                    try:
                        job_link = str(row.get('job_link', '')).strip()
                        job_name = str(row.get('job_name', '')).strip()
                        company_name = str(row.get('company_name', '')).strip()
                        salary = row.get('salary', '').strip()
                        # region = str(row.get('region', '')).strip()
                        # job_status = str(row.get('job_status', '')).strip()
                        # post_date = str(row.get('post_date', '')).strip()
                        # scrape_date = str(row.get('scrape_date', '')).strip() 
                        jd = str(row.get('jd', '')).strip()
                        jd = str(row.get('description', '')).strip()
                        hr_id = str(row.get('hr_id', '')).strip()
                        company_href = str(row.get('company_href', '')).strip()
                        industry_name = str(row.get('industry_name', 'Chưa phân loại')).strip()

                        if not job_link or not job_name or not company_name:
                            continue  # Bỏ qua dòng thiếu dữ liệu quan trọng

                        hr, _ = models.HR.objects.get_or_create(
                            name=hr_id if hr_id else "N/A",
                            defaults={'link': job_link}
                        )

                        company, _ = models.Company.objects.get_or_create(
                            company_name=company_name,
                            defaults={'company_link': company_href}
                        )

                        industry, _ = models.Industry.objects.get_or_create(
                            industry_name=industry_name,
                            defaults={'description': 'Chưa phân loại'}
                        )

                        job, created = models.Job.objects.get_or_create(
                            link_job=job_link,
                            defaults={
                                'job_name': job_name,
                                'salary': salary if salary else None,
                                # 'region': region,
                                # 'job_status': job_status,
                                # 'post_date': post_date,
                                # 'scrape_date': scrape_date,
                                'jd': jd,
                                # 'description': description,
                                'company': company,
                                'hr': hr,
                                'industry': industry,
                            }
                        )
                        # print(job)


                        results.append({
                            'status': 'success',
                            'job_name': job_name,
                            'company_name': company_name,
                            'created': created,
                        })
                    except Exception as e:
                        error_trace = traceback.format_exc()
                        results.append({
                            'status': 'error',
                            'job_name': job_name,
                            'company_name': company_name,
                            'error': str(e),
                            'traceback': error_trace
                        })

                return JsonResponse({'status': 'complete', 'results': results})
            except Exception as e:
                # return JsonResponse({'status': 'error', 'message': f"Có lỗi xảy ra: {str(e)}"})
                return JsonResponse({'status': 'error', 'message': f"Có lỗi xảy ra: {str(e)}", 'traceback': traceback.format_exc()})

    return render(request, 'job/import_jobs.html')

@login_required(login_url='sign_in')
def job_list(request):
    jobs = models.Job.objects.all()
    companies = models.Company.objects.all()
    industries = models.Industry.objects.all()
    hrs = models.HR.objects.all()

    # Apply filters
    job_name = request.GET.get('job_name', '').strip()
    # company_id = request.GET.get('company', '').strip()
    company_name = request.GET.get('company', '').strip()
    industry_id = request.GET.get('industry', '').strip()
    salary_min = request.GET.get('salary_min', '').strip()
    hr_id = request.GET.get('hr', '').strip()

    if job_name:
        jobs = jobs.filter(job_name__icontains=job_name)
    if company_name:
        jobs = jobs.filter(company__company_name__icontains=company_name)
    if industry_id:
        jobs = jobs.filter(industry_id=industry_id)
    if salary_min:
        jobs = jobs.filter(salary__gte=salary_min)
    if hr_id:
        jobs = jobs.filter(hr_id=hr_id)

    # Phân trang với 20 job mỗi trang
    paginator = Paginator(jobs, 20)
    page = request.GET.get('page')
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Check if the request is AJAX
        return render(request, 'job/job_table.html', {"jobs": jobs})

    context = {
        'jobs': jobs,
        'companies': companies,
        'industries': industries,
        'hrs': hrs,
    }
    return render(request, 'job/job_list.html', context)




@login_required(login_url='sign_in')
def recommended_jobs_by_department(request):
    # Lấy ngành học của sinh viên
    student = models.Student.objects.filter(user=request.user).first()
    department = student.department

    if not department:
        return render(request, 'job/job_table.html', {"jobs": [], "message": "Bạn chưa được liên kết với ngành học."})

    # Lọc các công việc theo ngành
    # jobs = models.Job.objects.filter(industry__description__icontains=department.name)
    jobs = models.Job.objects.all().order_by('-id')[:25]
    
    # Apply filters từ request.GET
    job_name = request.GET.get('job_name', '').strip()
    company_name = request.GET.get('company', '').strip()
    industry_id = request.GET.get('industry', '').strip()
    salary_min = request.GET.get('salary_min', '').strip()
    hr_id = request.GET.get('hr', '').strip()

    if job_name:
        jobs = jobs.filter(job_name__icontains=job_name)
    if company_name:
        jobs = jobs.filter(company__company_name__icontains=company_name)
    if industry_id:
        jobs = jobs.filter(industry_id=industry_id)
    if salary_min:
        jobs = jobs.filter(salary__gte=salary_min)
    if hr_id:
        jobs = jobs.filter(hr_id=hr_id)

    # Phân trang với 20 job mỗi trang
    paginator = Paginator(jobs, 20)
    page = request.GET.get('page')
    try:
        jobs = paginator.page(page)
    except PageNotAnInteger:
        jobs = paginator.page(1)
    except EmptyPage:
        jobs = paginator.page(paginator.num_pages)


    if request.headers.get('x-requested-with') == 'XMLHttpRequest': 
        return render(request, 'job/job_table.html', {"jobs": jobs})

    context = {
        "jobs": jobs,
        "department": department,
    }
    return render(request, 'job/job_list.html', context)






@login_required(login_url='sign_in')
def recommended_jobs_by_cv(request, pk):
    cv = models.CV.objects.filter(pk=pk).last()
    if not cv:
        return JsonResponse({"jobs": [], "message": "CV not found."})

    cv_data = {
        "skills": [skill.skill.skill for skill in models.SkillinCV.objects.filter(cv=cv)],
        "experiences": [exp.experience.role for exp in models.ExperienceinCV.objects.filter(cv=cv)],
        "projects": [proj.project_name for proj in models.Project.objects.filter(cv=cv)],
    }

    jobs = models.Job.objects.select_related("company", "industry", "hr").all()
    
    job_data = [
        {
            "job_name": job.job_name,
            "company": job.company.company_name if job.company else "N/A",
            "industry": job.industry.industry_name if job.industry else "N/A",
            "hr": job.hr.name if job.hr else "N/A",
            "salary": job.salary,
            "jd": job.jd,
            "link_job": job.link_job
        }
        for job in jobs
    ]

    recommended_jobs = nlp.process_cv_to_jobs(cv_data, job_data)
    

    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({"jobs": recommended_jobs.to_dict(orient='records')})

    context = {
        "cv": cv,
        "jobs": recommended_jobs.to_dict(orient='records'),
    }
    
    return render(request, 'job/job_table.html', context)


###################################
######## Module Chatbot gemini ####


import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
import os

# @csrf_exempt
# Cấu hình API Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


generation_config = {
    "temperature": 1.55,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Tạo model chatbot
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)

chat_session = model.start_chat(history=[])

def chat_with_gemini(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").strip()

            if user_message:
                response = chat_session.send_message(user_message)
                return JsonResponse({"response": response.text})
            else:
                return JsonResponse({"error": "Tin nhắn không hợp lệ."}, status=400)

        except Exception as e:
            return JsonResponse({"error": f"Lỗi: {str(e)}"}, status=500)

    return JsonResponse({"error": "Phương thức không hợp lệ."}, status=405)


#############################
# Module Chatting & chatbot
#############################

@login_required(login_url='sign_in')
def chat_with_admin(request):
    user1 = request.user
    user2 = User.objects.filter(is_superuser=True).first()
    
    # if not user2:
    #     return render(request, 'chat/room_list.html', {'error': 'Không tìm thấy admin.'})

    # Tạo hoặc lấy phòng chat với admin
    room, created = models.PrivateChatRoom.objects.get_or_create(
        user1=min(user1, user2, key=lambda u: u.id),
        user2=max(user1, user2, key=lambda u: u.id)
    )

    return redirect('chat_dashboard_with_room', room_id=room.id)




@login_required(login_url='sign_in')
def chat_dashboard(request, room_id=None):
    # Lấy danh sách các phòng chat
    rooms = models.PrivateChatRoom.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).annotate(last_message_time=Max('messages__created_at')).order_by('-last_message_time')

    # Gán tin nhắn cuối cùng và tên hiển thị cho mỗi phòng
    for room in rooms:
        last_message = models.ChatMessage.objects.filter(room=room).order_by('-created_at').first()
        room.last_message = f"{last_message.sender.username}: {last_message.message[:30]}..." if last_message else "Chưa có tin nhắn nào."
        # room.display_username = room.user2.username if room.user1 == request.user else room.user1.username
        # room.display_username = "Phòng hỗ trợ sinh viên" if chat_partner.is_superuser else chat_partner.username
        chat_partner = room.user2 if room.user1 == request.user else room.user1
        room.display_username = "Phòng hỗ trợ sinh viên" if chat_partner.is_superuser else chat_partner.username

    # Nếu có `room_id`, lấy tin nhắn của phòng đó
    messages = []
    chat_partner_name = ""
    if room_id:
        room = models.PrivateChatRoom.objects.get(id=room_id)
        messages = models.ChatMessage.objects.filter(room=room).order_by('created_at')
        chat_partner = room.user1 if room.user2 == request.user else room.user2
        chat_partner_name = "Phòng hỗ trợ sinh viên" if chat_partner.is_superuser else chat_partner.username

    context = {
        'rooms': rooms,
        'room_id': room_id,
        'messages': messages,
        'chat_partner_name': chat_partner_name,
    }
    return render(request, 'chat/dashboard.html', context)


@login_required(login_url='sign_in')
def chat_with_bot(request):
    """Tạo hoặc lấy phòng chat với ChatBot Assistant."""
    bot_user, created = User.objects.get_or_create(
        username="ChatBot_Assistant",
        defaults={"is_active": True, "is_superuser": False}
    )

    # Tạo hoặc lấy phòng chat với chatbot
    room, created = models.PrivateChatRoom.objects.get_or_create(
        user1=min(request.user, bot_user, key=lambda u: u.id),
        user2=max(request.user, bot_user, key=lambda u: u.id)
    )

    return redirect('chat_dashboard_with_room', room_id=room.id)

