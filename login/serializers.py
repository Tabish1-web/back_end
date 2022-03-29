import os

from django.contrib.auth import authenticate
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from login.google import Google
from .models import User
from social.models import RedditMessage, Twitter, Reddit, TwitterMessage

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=80, min_length=8, write_only=True)
    
    class Meta:
        model = User
        fields = ["email", "username", "password"]

    def validate(self, attrs):
        password = attrs.get("password","")

        attrs['image'] = None

        if not password:
            raise serializers.ValidationError({
                "password":"password is required!"
            })

        if len(password) < 8:
            raise serializers.ValidationError("password must be at least 8 characters")

        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class EmailVerificationSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=555)

    class Meta:
        model = User
        fields = ['token']

class GoogleSerializer(serializers.Serializer):
    auth_token = serializers.CharField()

    def validate_auth_token(self, auth_token):
        user_data = Google.validate(auth_token=auth_token)
        
        try:
            user_data['sub']
        except:
            raise serializers.ValidationError("token is expired or invalid!")
        
        if user_data['aud'] != os.environ.get("GOOGLE_CLIENT_ID"):
            raise AuthenticationFailed("oops! authentication error")

        email = user_data['email']
        username = user_data['name']
        img = user_data['picture']
        provider = 'google'

        email_exist = User.objects.filter(email=email)

        if email_exist and email_exist[0].auth_provider != provider:
            raise AuthenticationFailed(f'your email is already register onlygrow') 

        filter_email = User.objects.filter(email=email,auth_provider=provider)

        if filter_email.exists():
            return self.email_exist(email)

        else:
            return self.email_not_exist(username, email, img, provider)

    
    def email_exist(self, email):
        user = authenticate(email=email, password=os.environ.get("SOCIAL_PASSWORD"))
            
        return {
            "tokens" : user.tokens()
        }
    
    def email_not_exist(self, username, email, img, provider):
        user = {"username" : username, "email" : email, "image" : img, 
            "password" : os.environ.get("SOCIAL_PASSWORD")}

        user = User.objects.create_user(**user)
        user.is_verify = True
        user.auth_provider = provider
        user.save()

        new_user = authenticate(email=email, password=os.environ.get("SOCIAL_PASSWORD"))
        return {
            "tokens" : new_user.tokens()
        }

class LoginSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=255, min_length=5, write_only=True)
    password = serializers.CharField(max_length=80, min_length=8, write_only=True)
    tokens = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["email", "password", "tokens"]

    def get_tokens(self, data):
        tokens = data.get('tokens')
        tokens = tokens()
        return {
            "refresh" : tokens["refresh"],
            "access" : tokens["access"]
        }

    def validate(self, attrs):
        email = attrs.get("email", "")
        password = attrs.get("password", "")
        
        get_user = User.objects.filter(email=email)

        user = authenticate(email=email, password=password)

        if get_user.exists() and get_user[0].auth_provider != "email":
            raise AuthenticationFailed(f"your email is register as {get_user[0].auth_provider}")
        
        if not user:
            raise AuthenticationFailed("invalid credientials!")

        if not user.is_active:
            raise AuthenticationFailed("user is not active!")
        
        if not user.is_verify:
            raise AuthenticationFailed("verify your email!")

        return {
            "tokens" : user.tokens
        }

class TwitterMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwitterMessage
        fields = ["message", "pause"]

class TwitterSerializer(serializers.ModelSerializer):
    direct_message = TwitterMessageSerializer(many=False, read_only=True)
    class Meta:
        model = Twitter
        fields = ["twitter_name", "twitter_screen_name", "direct_message"]

class RedditMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedditMessage
        fields = ["message", 'pause']

class RedditSerializer(serializers.ModelSerializer):
    direct_message = RedditMessageSerializer(many=False, read_only=True)
    class Meta:
        model = Reddit
        fields = ["user_reddit_name","direct_message"]

class GetUserFromTokenSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True)
    email = serializers.CharField(max_length=255, min_length=5, read_only=True)
    username = serializers.CharField(max_length=255, min_length=3, read_only=True)
    profile_pic = serializers.ImageField(read_only=True)
    twitter = TwitterSerializer(many=False, read_only=True)
    reddit = RedditSerializer(many=False, read_only=True)
    
    def validate(self, attrs):
        user_id = attrs.get('user_id')
        
        user = User.objects.filter(id=user_id).first()
        
        twitter = self.get_twitter(user=user)
        reddit = self.get_reddit(user=user)

        if user:
            return {
                "email" : user.email,
                "username" : user.username,
                "profile_pic" : user.image,
                "twitter" : twitter,
                "reddit" : reddit
            }
        raise AuthenticationFailed("not found any user!")    

    def get_twitter(self, user):
        return Twitter.objects.filter(user=user).first()

    def get_reddit(self, user):
        return Reddit.objects.filter(user=user).first()

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_message = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()

        except TokenError:
            self.fail('bad_token')

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    class Meta:
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email','')
        
        user = User.objects.filter(email=email)

        if not email:
            raise serializers.ValidationError("email is required!")

        if not user:
            raise AuthenticationFailed(f'{email} is not register!')

        if user and user[0].auth_provider != "email":
            raise AuthenticationFailed(f'your email is register as {user[0].auth_provider}')

        return attrs

class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        min_length=6, max_length=68, write_only=True)
    token = serializers.CharField(
        min_length=1, write_only=True)
    uidb64 = serializers.CharField(
        min_length=1, write_only=True)

    class Meta:
        fields = ['password', 'token', 'uidb64']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')

            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)
            password_reset_token = PasswordResetTokenGenerator()
            if not password_reset_token.check_token(user, token):
                raise AuthenticationFailed('The reset link is invalid', 401)

            user.set_password(password)
            user.save()

            return (user)

        except Exception as e:
            raise AuthenticationFailed('The reset link is invalid', 401)
        