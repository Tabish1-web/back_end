from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from post.models import RedditPost, TwitterPost, User
from .serializers import (
    GetRedditSerializer, GetTwitterSerializer, 
    SaveMediaSerializer, SaveRedditSerializer, 
    SaveTweetStatusSerializer
)
from rest_framework.pagination import PageNumberPagination
from django.core.files.base import File
from social.utils import get_scheduler
import uuid

User = get_user_model()

# save post views

class SaveMediaView(generics.GenericAPIView):
    serializer_class = SaveMediaSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):

        # get media data
        data = request.data['media']

        # create file from bytesio
        file = self.create_file(data=data)

        # set data
        data = dict(file=file)

        # serializing
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        # response
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

    def create_filename(self, name):
        filename, ext = name.split(".")
        name = f'{filename}-{uuid.uuid4()}.{ext}'
        return name

    def create_file(self, data):
        name = data.name
        filename = self.create_filename(name=name)
        io_file = data.file
        file = File(io_file, name=filename)
        return file


class SaveTweetStatusView(generics.GenericAPIView):
    serializer_class = SaveTweetStatusSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):

        data = request.data

        # current user id with data
        user_id = request.user.id
        data['user'] = user_id

        # get current request data
        comment = data.get('comment', None)
        postOn = data.get('postOn', None)
        
        # remove empty data 
        not comment and data.pop('comment')
        not postOn and data.pop('postOn')
       
        # serializing
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        # response
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

class SaveRedditView(generics.GenericAPIView):
    serializer_class = SaveRedditSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        
        data = request.data
        
        # current user id with data
        user_id = request.user.id
        data['user'] = user_id

        # get current request data
        comment = data.get('comment', None)
        link = data.get('link', None)
        body = data.get('body', None)
        postOn = data.get('postOn', None)

        # remove empty data 
        not link and data.pop('link')
        not body and data.pop('body')
        not comment and data.pop('comment')
        not postOn and data.pop('postOn')

        # serializing
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        # response 
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response

# end save post views

# get post list views

class ResultsSetPagination(PageNumberPagination):
    page_size = 4
    page_size_query_param = 'page_size'
    max_page_size = 4

class GetTwitterView(generics.GenericAPIView):
    serializer_class = GetTwitterSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = ResultsSetPagination
    
    def get(self, request):
        
        # get current user
        user = request.user
        twitter_id = request.GET.get("tweet_id", None)
        # analytics = request.GET.get("analytics", None)
        page = int(request.GET.get("page", 1))
        
        # single tweet
        if twitter_id:
            twitter = user.twitter_posts.filter(id=int(twitter_id)).first()
            serializer = self.serializer_class(twitter)
            data = serializer.data
            response = Response(data=data, status=status.HTTP_200_OK)
            return response
        
        # filter twitter post by user

        tweets = user.twitter_posts.all()
        

        for i in range((page-1)*4, page*4):
            if len(tweets) > i:
                tweet = tweets[i]
                tweet.get_analytics_data
            else:
                break

        # filter tweets with analytics    
        tweets = user.twitter_posts.all()
        
        # response
        response = self.get_paginated_response(
            self.paginate_queryset(self.serializer_class(tweets, many=True).data))
        return response

    def delete(self, request):

        # get request data
        tweet_id = int(request.GET['tweet_id'])
        user = request.user
        
        # filter tweet
        tweet = TwitterPost.objects.filter(id=tweet_id, user=user).first()
        
        # tweet not found response
        if not tweet:
            data = dict(message="tweet not found")
            response = Response(data=data, status=status.HTTP_404_NOT_FOUND)
            return response
        
        # delete tweet (server, twitter)
        tweet.delete_tweet
        tweet.delete()
        
        # response
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response

class GetRedditView(generics.GenericAPIView):
    queryset = RedditPost.objects.all()
    serializer_class = GetRedditSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = ResultsSetPagination
    
    def get(self, request):
        
        # get current user
        user = request.user
        reddit_id = request.GET.get("reddit_id", None)
        # analytics = request.GET.get("analytics", None)
        page = int(request.GET.get("page", 1))

        # single reddit
        if reddit_id:
            reddit = user.reddit_posts.filter(id=int(reddit_id)).first()
            serializer = self.serializer_class(reddit)
            data = serializer.data
            response = Response(data=data, status=status.HTTP_200_OK)
            return response

        reddits = user.reddit_posts.all() 
        

        for i in range((page-1)*4, page*4):
            if len(reddits) > i:
                reddit = reddits[i]
                reddit.get_analytics_data
            else:
                break
        
        # filter reddit post
        # reddits = user.reddit_posts.all()
        # [reddit.get_analytics_data for reddit in reddits if analytics]

        # again filter reddit post with analytics
        reddits = user.reddit_posts.all() 

        # response
        response = self.get_paginated_response(
            self.paginate_queryset(self.serializer_class(reddits, many=True).data))
        return response
    
    def delete(self, request):

        # get request data
        user = request.user
        reddit_id = int(request.GET['reddit_id'])
        
        # filter reddit
        reddit = RedditPost.objects.filter(id=reddit_id, user=user).first()

        # reddit not found response 
        if not reddit:
            data = dict(message="reddit not found")
            response = Response(data=data, status=status.HTTP_404_NOT_FOUND)
            return response
        
        # delete reddit (server, reddit)
        reddit.delete_reddit
        reddit.delete()

        # response 
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return response
    
    def put(self, request):

        # get request data 
        data = request.data
        reddit_id = request.GET.get("reddit_id")
        user = request.user
        
        # filter reddit 
        reddit = RedditPost.objects.filter(id=reddit_id).first()
       
        # create new data
        new_data = {
            "title" : reddit.title,
            "body" : data["redditBodyContent"],
            "comment" : data["comment"],
            "nsfw" : reddit.nsfw,
            "post_time" : reddit.post_time,
            "user" : user.id,
            "sub_reddit" : reddit.sub_reddit,
        }
        
        # serializing
        serializer = self.serializer_class(reddit ,data=new_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = serializer.data
        
        # edit reddit
        reddit.edit_reddit
        
        # response
        response = Response(data=data, status=status.HTTP_201_CREATED)
        return response
