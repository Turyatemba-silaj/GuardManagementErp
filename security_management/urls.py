"""
URL configuration for security_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from core.auth_views import DatabaseSafeLoginView, HomeRedirectAdminLoginView

urlpatterns = [
    path('', include('core.urls')),
    path('accounts/login/', DatabaseSafeLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/login/', HomeRedirectAdminLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    from django.contrib.staticfiles.views import serve as serve_static

    urlpatterns.insert(0, re_path(r"^static/(?P<path>.*)$", serve_static, name="static"))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
