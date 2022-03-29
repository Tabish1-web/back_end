from io import BytesIO
import os

from django.core import files
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)

import requests
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from rest_framework_simplejwt.tokens import RefreshToken

class UserManager(BaseUserManager):
    
    def create_user(self, username, email, password=None, image=None):
        if username is None:
            raise TypeError("username is required!")
        if email is None:
            raise TypeError("email is required!")

        if image:
            resp = requests.get(image)
            if resp.status_code != requests.codes.ok:
                raise Exception("image not found")
            fp = BytesIO()
            fp.write(resp.content)
            file_name = f"{uuid.uuid4()}.png" 
            user = self.model(username=username, email=self.normalize_email(email))
            user.image = file_name
            user.image.save(file_name, files.File(fp))
        else:
            user = self.model(username=username, email=self.normalize_email(email))
            user.image = "uploads/user/profile/user.png"
        
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, username, email, password=None):
        if password is None:
            raise TypeError("password is required!")

        user = self.create_user(username, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return user

AUTH_PROVIDERS = {"google" : "google", "email" : "email"}

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    is_verify = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    image = models.ImageField(upload_to="uploads/user/profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    auth_provider = models.CharField(max_length=255, blank=False,null=False,
        default=AUTH_PROVIDERS.get('email'))
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def __str__(self) -> str:
        return self.email

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }
    
    def start(self):
        if hasattr(self, "twitter"):
            scheduler = BackgroundScheduler()
            scheduler.add_job(self.twitter.send_direct_messages , 'interval', minutes=1)
            scheduler.start()