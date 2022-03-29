from django.core.mail import EmailMessage
from django.urls import reverse
from django.conf import settings
from rest_framework import generics, status, views, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import smart_str, smart_bytes, DjangoUnicodeDecodeError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpResponsePermanentRedirect
from django.forms.models import model_to_dict
from .serializers import (
    GetUserFromTokenSerializer, GoogleSerializer, LoginSerializer, LogoutSerializer,
    RegisterSerializer, EmailVerificationSerializer, ResetPasswordSerializer, SetNewPasswordSerializer)
from rest_framework.response import Response
from .models import User
from .renders import UserRenderer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import threading
import jwt
import os

class EmailThread(threading.Thread):
    def __init__(self, email) -> None:
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    renderer_classes = (UserRenderer,)

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        user = User.objects.get(email=user_data['email'])
        refresh = RefreshToken.for_user(user)
        token = refresh.access_token
        current_site = get_current_site(request=request)
        domain = current_site.domain
        relative_link = reverse("email-verify")
        absolute_url = self.absolute_url(domain, relative_link, token)
        email_body = self.email_body(user, absolute_url)
        data = self.email_data(user, email_body)
        self.send_email(data)
        return Response(user_data, status=status.HTTP_201_CREATED)
            
    def absolute_url(self, domain, relative_link, token):
        return "http://" + domain + relative_link + "?token=" + str(token)

    def email_body(self, user, absolute_url):
        return "Hi " + user.username + \
            "\n" + "Please use this link for verify email" + "\n" + \
            absolute_url

    def email_data(self, user, email_body):
        return {"body" : email_body, "to" : user.email, 
            "subject" : "verify your email"}

    def send_email(self, data):
        email = EmailMessage(subject=data['subject'], body=data['body'],
            to=[data['to']])
        email_thread = EmailThread(email)
        email_thread.start()

class VerifyEmail(views.APIView):
    serializer_class = EmailVerificationSerializer

    token_param_config = openapi.Parameter(
        'token', in_=openapi.IN_QUERY, description='Description', type=openapi.TYPE_STRING)

    @swagger_auto_schema(manual_parameters=[token_param_config])
    def get(self, request):
        token = request.GET.get('token')
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = User.objects.get(id=payload['user_id'])
            if not user.is_verify:
                user.is_verify = True
                user.save()
            frontend_url = os.environ.get("FRONTEND_URL")
            return HttpResponsePermanentRedirect(frontend_url + "/login")
        except jwt.ExpiredSignatureError as identifier:
            return Response({'error': 'Activation Expired'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.exceptions.DecodeError as identifier:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

class GoogleView(generics.GenericAPIView):
    serializer_class = GoogleSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data['auth_token']
        response = Response(data=data, status=status.HTTP_200_OK)
        return response

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GetUserFromTokenView(generics.GenericAPIView):    
    serializer_class = GetUserFromTokenSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        user_id = request.user.id
        serializer = self.serializer_class(data=dict(user_id=user_id))
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class LogoutView(generics.GenericAPIView):    
    serializer_class = LogoutSerializer

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

class PasswordResetView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    # renderer_classes = (UserRenderer,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email', '')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            current_site = get_current_site(request=request)
            domain = current_site.domain
            relative_link = reverse('password-reset-confirm',
                kwargs={'uidb64': uidb64, 'token': token})

            redirect_url = os.environ.get("FRONTEND_URL") + "/set-password"
            absurl = 'http://'+ domain + relative_link
            body = f'Hi {user.username}, Password reset link \n {absurl}?redirect_url={redirect_url}'
            data = {
                'body': body, 
                'to': user.email,
                'subject': 'Reset your passsword'
            }
            self.send_email(data)
            return Response({'success': 'We have sent you a link to reset your password'}, status=status.HTTP_200_OK)
        return Response(serializer.data)


    def send_email(self, data):
        email = EmailMessage(subject=data['subject'], body=data['body'], to=[data['to']])
        email_thread = EmailThread(email)
        email_thread.start()

class PasswordTokenView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def get(self, request, uidb64, token):
        redirect_url = request.GET.get('redirect_url')

        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                if len(redirect_url) > 3:
                    return HttpResponsePermanentRedirect(redirect_url+'?token_valid=False')
                else:
                    return HttpResponsePermanentRedirect(os.environ.get('FRONTEND_URL', '')+'?token_valid=False')

            if redirect_url and len(redirect_url) > 3:
                return HttpResponsePermanentRedirect(redirect_url+'?token_valid=True&message=Credentials Valid&uidb64='+uidb64+'&token='+token)
            else:
                return HttpResponsePermanentRedirect(os.environ.get('FRONTEND_URL', '')+'?token_valid=False')

        except DjangoUnicodeDecodeError as identifier:
            try:
                if not PasswordResetTokenGenerator().check_token(user):
                    return HttpResponsePermanentRedirect(redirect_url+'?token_valid=False')
                    
            except UnboundLocalError as e:
                return Response({'error': 'Token is not valid, please request a new one'}, status=status.HTTP_400_BAD_REQUEST)

class SetNewPasswordView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'success': True, 'message': 'Password reset success'}, status=status.HTTP_200_OK)