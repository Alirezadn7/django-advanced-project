from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

@transaction.atomic
def update_account(* , user ,  password=None) -> User:
    
    if password is not None :
        user.set_password(password)
        user.save()
    
    return user