import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\Users\satvi\OneDrive\Desktop\ascent\Veil')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Veil.settings')
django.setup()

from Veil_app.models import ChatSession

def close_all_sessions():
    active_sessions = ChatSession.objects.filter(is_active=True)
    count = active_sessions.count()
    if count > 0:
        print(f"Closing {count} active sessions...")
        active_sessions.update(is_active=False)
        print("All sessions closed.")
    else:
        print("No active sessions found.")

if __name__ == "__main__":
    close_all_sessions()
