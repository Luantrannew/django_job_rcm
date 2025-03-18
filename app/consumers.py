import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import PrivateChatRoom, ChatMessage, Student, CV, Job, SkillinCV, ExperienceinCV, Project
from django.contrib.auth.models import User
from channels.db import database_sync_to_async
from . import nlp


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = data['sender_id']

        sender = await self.get_user(sender_id)
        room = await self.get_room(self.room_id)

        chat_message = await self.save_message(room, sender, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender.username,
                'sender_id': sender.id,
                'created_at': str(chat_message.created_at),
                'is_superuser': sender.is_superuser,
            }
        )

        bot_username = "ChatBot_Assistant"
        if await self.is_chat_with_bot(room):
            bot_response = await self.generate_bot_response(message, sender.is_superuser, sender)
            bot_user = await self.get_user_by_username(bot_username)

            bot_message = await self.save_message(room, bot_user, bot_response)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': bot_response,
                    'sender': bot_user.username,
                    'sender_id': bot_user.id,
                    'created_at': str(bot_message.created_at),
                    'is_superuser': False,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    @database_sync_to_async
    def get_user_by_username(self, username):
        return User.objects.get_or_create(username=username, defaults={"is_active": True})[0]

    @database_sync_to_async
    def get_room(self, room_id):
        return PrivateChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def save_message(self, room, sender, message):
        return ChatMessage.objects.create(room=room, sender=sender, message=message)

    @database_sync_to_async
    def is_chat_with_bot(self, room):
        bot_user = User.objects.filter(username="ChatBot_Assistant").first()
        return room.user1 == bot_user or room.user2 == bot_user

    @database_sync_to_async
    def lookup_student_info(self, student_code):
        student = Student.objects.filter(student_code=student_code).first()
        if not student:
            return f"❌ Không tìm thấy sinh viên với mã: {student_code}"
        return (
            f"🎓 Thông tin sinh viên:\n"
            f"- Họ tên: {student.name}\n"
            f"- Mã sinh viên: {student.student_code}\n"
            f"- Email: {student.email}\n"
            f"- Số điện thoại: {student.phone}\n"
            f"- Năm học: {student.study_year}\n"
            f"- Ngành: {student.department.name if student.department else 'Chưa có'}"
        )
    
    @database_sync_to_async
    def get_cv_list(self, user):
        """Liệt kê tất cả CV của người dùng."""
        student = Student.objects.filter(user=user).first()
        if not student:
            return "❌ Bạn chưa có CV nào."

        cvs = CV.objects.filter(student=student)
        if not cvs:
            return "❌ Bạn chưa có CV nào."

        response = "📄 Danh sách CV của bạn:\n"
        for cv in cvs:
            response += f"🔹 {cv.name} (🆔 {cv.id}, 📅 {cv.create_date or 'Không có ngày tạo'})\n"
            response += f"   <a href='http://127.0.0.1:8000/cv/{cv.id}/'>Xem chi tiết CV ở đây</a>\n"
            response += f"  - Nhắn lệnh sau để xóa CV {cv.id} (/cv delete {cv.id})\n"
            response += f"  - Nhắn lệnh sau để có các job đề xuất phù hợp (/cv jobs {cv.id})\n\n"

        return response.strip()

    @database_sync_to_async
    def delete_cv(self, user, cv_id):
        """Xóa CV theo ID."""
        student = Student.objects.filter(user=user).first()
        if not student:
            return "❌ Bạn không có quyền xóa CV này."

        cv = CV.objects.filter(id=cv_id, student=student).first()
        if not cv:
            return f"❌ Không tìm thấy CV với ID: {cv_id}"

        cv.delete()
        return f"✅ CV '{cv.name}' đã được xóa thành công."

    @database_sync_to_async
    def get_cv_jobs(self, user, cv_id):
        """Trả về danh sách công việc phù hợp với CV bằng NLP."""
        cv = CV.objects.filter(id=cv_id, student__user=user).first()
        if not cv:
            return f"❌ Không tìm thấy CV với ID: {cv_id}"

        # Lấy dữ liệu từ CV
        cv_data = {
            "skills": [skill.skill.skill for skill in SkillinCV.objects.filter(cv=cv)],
            "experiences": [exp.experience.role for exp in ExperienceinCV.objects.filter(cv=cv)],
            "projects": [proj.project_name for proj in Project.objects.filter(cv=cv)],
        }

        # Lấy danh sách công việc từ database
        jobs = Job.objects.select_related("company", "industry", "hr").all()
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

        # Gọi NLP để xử lý gợi ý công việc
        recommended_jobs = nlp.process_cv_to_jobs(cv_data, job_data).head(5)  # Lấy top 5 công việc phù hợp

        if recommended_jobs.empty:
            return f"❌ Không có công việc nào phù hợp với CV '{cv.name}'."

        # Tạo danh sách công việc trả về chatbot
        response = f"💼 **Công việc phù hợp với CV '{cv.name}':**\n\n"
        for _, job in recommended_jobs.iterrows():
            response += f"🔹 **{job['job_name']}** tại **{job['company']}**\n"
            response += f"   🔗 <a href='{job['link_job']}'>Xem chi tiết</a>\n\n"

        return response.strip()

    @database_sync_to_async
    def get_cv_view_link(self, user, cv_id):
        """Trả về đường dẫn đến trang chi tiết của CV."""
        cv = CV.objects.filter(id=cv_id, student__user=user).first()
        if not cv:
            return f"❌ Không tìm thấy CV với ID: {cv_id}"

        return f"🔗 <a href='http://127.0.0.1:8000/cv/{cv.id}/'>Xem chi tiết CV '{cv.name}'</a>"

    async def generate_bot_response(self, message, is_admin, user):

        if message.startswith("/admin"):
            if not is_admin:
                return "⛔ Bạn không có quyền sử dụng lệnh này!"

            command_parts = message.split()
            if len(command_parts) == 1:
                return "⚠️ Vui lòng nhập lệnh sau /admin. Ví dụ: '/admin status' hoặc '/admin lookup'."

            command = command_parts[1]
            if command == "status":
                return "✅ Bot đang hoạt động bình thường."

            elif command == "lookup":
                if len(command_parts) != 3:
                    return "⚠️ Lệnh không đúng. Sử dụng: `/admin lookup [student_code]`."
                student_code = command_parts[2]
                return await self.lookup_student_info(student_code)

            else:
                return f"⚠️ Không nhận diện được lệnh: '{command}'"
            
        # Xử lý lệnh kiểm tra CV
        elif message.startswith("/cv"):
            command_parts = message.split()
            
            if len(command_parts) == 1:
                return await self.get_cv_list(user)

            elif len(command_parts) == 3 and command_parts[1] == "delete":
                return await self.delete_cv(user, command_parts[2])

            elif len(command_parts) == 3 and command_parts[1] == "jobs":
                return await self.get_cv_jobs(user, command_parts[2])
            
            elif len(command_parts) == 3 and command_parts[1] == "view":
                return await self.get_cv_view_link(user, command_parts[2])
            
        elif message.lower() == "help":
            help_message = (
                "🤖 **Hướng dẫn sử dụng ChatBot:**\n\n"
                "💬 **Lệnh cho người dùng:**\n"
                "- `/cv` - Xem danh sách CV của bạn.\n"
                "- `/cv view [cv_id]` - Xem chi tiết CV theo ID.\n"
                "- `/cv delete [cv_id]` - Xóa CV theo ID.\n"
                "- `/cv jobs [cv_id]` - Xem công việc phù hợp với CV.\n\n"
                "🛠️ **Lệnh cho Admin:**\n"
                "- `/admin status` - Kiểm tra trạng thái bot.\n"
                "- `/admin lookup [student_code]` - Tra cứu thông tin sinh viên.\n\n"
                "📄 **Cách sử dụng:**\n"
                "- Gõ lệnh theo đúng định dạng. Ví dụ: `/cv view 5` để xem CV có ID là 5.\n"
                "- Sử dụng `help` bất kỳ lúc nào để xem hướng dẫn này.\n\n"
                "🚀 **Lưu ý:** Một số lệnh chỉ khả dụng nếu bạn là quản trị viên."
            )
            return help_message

        return f"🤖 ChatBot: Chào bạn, nếu cần giúp đỡ về các câu lệnh, hãy gõ 'help' để xem hướng dẫn."
