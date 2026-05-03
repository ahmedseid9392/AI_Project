from datetime import datetime


def site_context(request):
    return {
        'site_name': 'Student Performance System',
        'current_year': datetime.now().year,
    }
