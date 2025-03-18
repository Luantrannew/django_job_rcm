import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from app import consumers  
import app.routing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'due_job_rcm.settings')


application = get_asgi_application()
application = ProtocolTypeRouter({
  'http': get_asgi_application(),
  'websocket' : AuthMiddlewareStack(
      URLRouter(
          app.routing.websocket_urlpatterns
      )
  )
})


