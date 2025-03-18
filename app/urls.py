from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('',views.index,name='index'),
    
    path('sign-in/',views.sign_in,name='sign_in'),
    path('logout/', views.logout_view, name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

    path('profile/change-password/', views.change_password, name='change_password'),
    

    # quản lý CV
    path('student-register', views.student_form, name='studentForm'),
    path('get-student-info/<int:pk>/', views.get_student_info, name='get_student_info'),
    path('import-student/',views.import_csv,name='import_student'),
    path('admin-students/', views.student_management, name='student_management'),


    path('cv/listview/',views.cv_list, name='cv_list'), 
    path('cv/<int:pk>/', views.cv_detail, name='cv_detail'),
    path('update-cv/<int:pk>/', views.update_cv, name='update_cv'),
    path('delete-cv/<int:pk>/', views.delete_cv, name='delete_cv'),
    path('cv/<int:pk>/recommended-jobs/', views.recommended_jobs_by_cv, name='recommended_jobs_by_cv'),
    path('cv-form/', views.cv_form, name='cv-form'),
    path('cv/<int:cv_id>/pdf/', views.generate_cv_pdf, name='generate_cv_pdf'),
    
    
    # quản lý Job
    path('jobs/', views.job_list, name='job_list'),
    path('import-job/',views.import_jobs,name='import_jobs'),
    path('department-jobs/', views.recommended_jobs_by_department, name='depart_recommended_jobs'),

    # quản lý chat  
    path("chatbotgemini/", views.chat_with_gemini, name="chat_with_gemini"),
 
    path('chat/', views.chat_dashboard, name='chat_dashboard'),
    path('chat/<int:room_id>/', views.chat_dashboard, name='chat_dashboard_with_room'),
    path('chat/bot/', views.chat_with_bot, name='chat_with_bot'),
    path('chat/admin/', views.chat_with_admin, name='chat_with_admin'),





]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
