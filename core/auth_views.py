from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, REDIRECT_FIELD_NAME, SESSION_KEY
from django.contrib.auth.views import LoginView
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect


def login_without_database_writes(request, user, backend):
    if SESSION_KEY in request.session:
        request.session.flush()
    else:
        request.session.cycle_key()
    request.session[SESSION_KEY] = str(user.pk)
    request.session[BACKEND_SESSION_KEY] = backend
    request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    rotate_token(request)


class DatabaseSafeLoginView(LoginView):
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = "registration/login.html"

    def form_valid(self, form):
        if getattr(settings, "DISABLE_LAST_LOGIN_UPDATE", False):
            user = form.get_user()
            login_without_database_writes(self.request, user, user.backend)
            return super(LoginView, self).form_valid(form)
        return super().form_valid(form)


class HomeRedirectAdminLoginView(LoginView):
    authentication_form = AdminAuthenticationForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = "admin/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context.setdefault("title", "Log in")
        return context

    def get_success_url(self):
        return settings.LOGIN_REDIRECT_URL

    def form_valid(self, form):
        if getattr(settings, "DISABLE_LAST_LOGIN_UPDATE", False):
            user = form.get_user()
            login_without_database_writes(self.request, user, user.backend)
            return redirect(self.get_success_url())
        return super().form_valid(form)
