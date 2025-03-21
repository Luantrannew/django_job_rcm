from django.db import models
from django.contrib.auth.models import User



#############################################
######## Module CV ##########################
#############################################

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Tên ngành học
    department_code = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Mã ngành học
    description = models.TextField(null=True, blank=True)  # Mô tả ngành học (tùy chọn)

    def __str__(self):
        if self.name and self.department_code:
            return f"{self.name} ({self.department_code})"
        elif self.name:
            return self.name
        elif self.department_code:
            return f"Mã ngành: {self.department_code}"
        return "Ngành học không có thông tin"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile",null=True)
    name = models.CharField(max_length=100)
    student_code = models.CharField(null=True, blank=True, max_length=20)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=False)
    study_year = models.TextField()
    department = models.ForeignKey('Department',on_delete=models.SET_NULL,null=True,blank=True)  # Liên kết với ngành học

    def __str__(self):
        return f"{self.pk}: {self.name} ({self.student_code})"

class CV(models.Model):
    name = models.CharField(max_length=100)  # tên cv 
    about_me = models.TextField(null=True, default=None)
    student = models.ForeignKey("Student", on_delete=models.SET_NULL, null=True, default=None)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    create_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

class SocialLink(models.Model):
    link = models.URLField(max_length=500,null=True, default=None)
    cv = models.ForeignKey("CV", on_delete=models.SET_NULL, null=True, default=None)
    
    def __str__(self):
        return self.link
    
class Displayname(models.Model) :
    social_link = models.ForeignKey("SocialLink",on_delete=models.SET_NULL, null=True, blank=True)
    display_name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self) :
        return self.display_name if self.display_name else f'dữ liệu null'
    
class Certification(models.Model):
    certificate = models.TextField(null=True, default=None)
    cv = models.ForeignKey("CV", on_delete=models.SET_NULL,null=True, default=None)

    def __str__(self):
        return f"{self.certificate}-{self.cv}" if self.certificate else f"dữ liệu null"

class Language(models.Model): 
    language = models.CharField(max_length=100,null=True, default=None)
    text = models.TextField(null=True, default=None)  # dùng để nhập mô tả (VD : communication như thế nào, ...)

    def __str__(self):
        return f"{self.language}"    
    
    
class Project(models.Model):
    project_name = models.CharField(max_length=200,null=True, default=None)
    project_content = models.TextField(null=True, default=None)
    cv = models.ForeignKey("CV", on_delete=models.SET_NULL,null=True, default=None)

class Project_link(models.Model):
    link = models.URLField(max_length=500,null=True, default=None)
    project = models.ForeignKey("Project", on_delete=models.SET_NULL,null=True, default=None)
    
    def __str__(self):
        return self.link if self.link else f"dữ liệu null"

class University(models.Model) : 
    university_name = models.CharField(max_length=100)

    def __str__(self):
        return self.university_name if self.university_name else f"dữ liệu null"


class Education(models.Model): # model này hiện tại chưa xài vì chỉ dùng cho khoa nên Education đều là DUE
    university = models.ForeignKey("University", on_delete=models.SET_NULL, null=True, default=None)
    degree = models.CharField(max_length=100, null=True, blank=True) 
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    text = models.TextField(null=True, default=None) # dùng để ghi chú bất kì thứ gì, có thể là điểm tổng, điểm môn 

    def __str__(self):
        return self.university if self.university else "Unknown University"
    
class Experience(models.Model):
    company_name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    context = models.TextField(null=True,blank=True)

    def __str__(self):
        return f"{self.role} at {self.company_name}"
    


class Skill(models.Model):
    skill = models.CharField(max_length=50)

    def __str__(self):
        return self.skill

class SkillinCV(models.Model): # mối quan hệ nhiều nhiều giữa skill và CV
    cv = models.ForeignKey("CV", on_delete=models.CASCADE)
    skill = models.ForeignKey("Skill", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cv.name} - {self.skill.skill}"
    

class ExperienceinCV(models.Model):    # mối quan hệ nhiều nhiều giữa kinh nghiệm và CV
    cv = models.ForeignKey("CV", on_delete=models.CASCADE)
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cv.name} - {self.experience}"


class EducationinCV(models.Model):     # mối quan hệ nhiều nhiều giữa education và CV
    cv = models.ForeignKey("CV", on_delete=models.CASCADE)
    education = models.ForeignKey("Education", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.education.university} - {self.cv.name}"


class LanguageinCV(models.Model):
    language = models.ForeignKey("Language", on_delete=models.CASCADE)
    cv = models.ForeignKey("CV", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.language.language}-{self.cv}"



#############################################
######## Module Job #########################
#############################################

class Company(models.Model):
    company_name = models.TextField(null=True, blank=True)
    company_link = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.company_name

# (chưa biết được làm như nào, làm trước nếu không có thì xử lí null, các job sẽ là chưa phân loại )
class Industry(models.Model):
    industry_name = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.industry_name


class HR(models.Model):
    name = models.TextField(null=True, blank=True)
    link = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    job_name = models.TextField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    link_job = models.TextField()
    jd = models.TextField() 

    hr = models.ForeignKey("HR", on_delete=models.CASCADE)
    company = models.ForeignKey("Company", on_delete=models.CASCADE)
    industry = models.ForeignKey("Industry", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.job_name
    

#############################################
######## Module chat ########################
#############################################


class PrivateChatRoom(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_room_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_room_user2")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat Room between {self.user1.username} and {self.user2.username}"

    class Meta:
        unique_together = ('user1', 'user2')    


class ChatMessage(models.Model):
    room = models.ForeignKey(PrivateChatRoom, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} in room {self.room.id}"

    class Meta:
        ordering = ['created_at'] 