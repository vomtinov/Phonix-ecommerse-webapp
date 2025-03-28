# user_panel/decorators.py
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def active_user_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
            messages.error(request, "Admin has blocked this user.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper