from rest_framework import generics, status, permissions
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from .serializers import (
    RedditMessageSerializer, RedditUrlSerializer, 
    SaveRedditUserSerializer, TwitterMessageSerializer,
    TwitterUrlSerializer, SaveTwitterUserSerializer,
    )

from .utils import get_scheduler

User = get_user_model()

class TwitterURLView(generics.GenericAPIView):
    serializer_class = TwitterUrlSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response = Response(data=data, status=status.HTTP_200_OK)
        return response

class SaveTwitterUserView(generics.GenericAPIView):
    serializer_class = SaveTwitterUserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        user_id = request.user.id
        data = request.data
        data['user_id'] = user_id
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

class DeleteTwitterUserView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def delete(self, request):
        user_id = request.user.id
        user = User.objects.get(pk=user_id)

        if not hasattr(user, "twitter"):
            data = dict(message="user has no twitter account")
            response = Response(data=data, status=status.HTTP_404_NOT_FOUND)
            return response
        
        try:
            dm_id = user.twitter.direct_message.id
            serializer = get_scheduler()
            serializer.remove_job(job_id=f"twitter-{dm_id}")
        except:
            pass 
        user.twitter.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

class TwitterMessageView(generics.GenericAPIView):
    serializer_class = TwitterMessageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        data = request.data
        
        # current user id with data
        user_id = request.user.id
        data['user_id'] = user_id

        # serializing
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        # response 
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

class RedditURLView(generics.GenericAPIView):
    serializer_class = RedditUrlSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response = Response(data=data, status=status.HTTP_200_OK)
        return response

class SaveRedditUserView(generics.GenericAPIView):
    serializer_class = SaveRedditUserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        user_id = request.user.id
        data = request.data
        data['user_id'] = user_id
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

class DeleteRedditUserView(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def delete(self, request):
        user_id = request.user.id
        user = User.objects.get(pk=user_id)

        if not hasattr(user, "reddit"):
            data = dict(message="user has no reddit account")
            response = Response(data=data, status=status.HTTP_404_NOT_FOUND)
            return response

        user.reddit.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

class RedditMessageView(generics.GenericAPIView):
    serializer_class = RedditMessageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        data = request.data
        
        # current user id with data
        user_id = request.user.id
        data['user_id'] = user_id

        # serializing
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        # response 
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response
