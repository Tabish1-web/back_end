from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('login.urls')),
    path('api/social/', include('social.urls')),
    path('api/post/', include('post.urls'))
]

urlpatterns += static(settings.MEDIA_URL,
            document_root=settings.MEDIA_ROOT)