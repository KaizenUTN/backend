from .models import User

def create_employee(username, email, password, role):
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role
    )
    return user