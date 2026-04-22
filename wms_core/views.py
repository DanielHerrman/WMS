from django.shortcuts import render

def error_403(request, exception=None):
    """
    Uživatelsky přívětivá stránka odepření přístupu pro moduly typu 3D Tisk.
    """
    return render(request, '403.html', status=403)
