import tweepy
import praw

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Reddit, RedditMessage, Twitter, TwitterMessage
from .utils import create_scheduler_job
import os
import random
import string

User = get_user_model()

class TwitterUrlSerializer(serializers.Serializer):

    def validate(self, attrs):
        consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
        consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
        redirect_url = os.environ.get("FRONTEND_URL") + "/account"

        auth = self.get_auth(consumer_key, consumer_secret, redirect_url)
        url = self.get_url(auth) 

        return dict(url=url)
    
    def get_auth(self, consumer_key, consumer_secret, redirect_url):
        auth = tweepy.OAuth1UserHandler(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            callback=redirect_url
        )
        return auth
    
    def get_url(self, auth):
        url = auth.get_authorization_url(signin_with_twitter=True)
        return url

class SaveTwitterUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True)
    oauth_token = serializers.CharField()
    oauth_verifier = serializers.CharField()


    def validate(self, attrs):
        consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
        consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
        oauth_token = attrs.get('oauth_token','')
        oauth_verifier = attrs.get('oauth_verifier','')
        redirect_url = os.environ.get("FRONTEND_URL") + "/account"
        user_id = attrs.get("user_id")

        try:
            user = User.objects.get(pk=user_id)

            auth = tweepy.OAuth1UserHandler(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                callback=redirect_url
            )

            auth.request_token = {
                "oauth_token" : oauth_token,
                "oauth_token_secret" : oauth_verifier
            }
            
            access_token, access_token_secret = auth.get_access_token(verifier=oauth_verifier)
            api = tweepy.API(auth)

            verify_credentials = api.verify_credentials()
            user_twitter_id = verify_credentials.id
            twitter_name = verify_credentials.name
            twitter_screen_name = verify_credentials.screen_name
            
            self.save_twitter_user(user=user,access_token=access_token, 
                access_token_secret=access_token_secret, user_twitter_id=user_twitter_id,
                twitter_name=twitter_name, twitter_screen_name=twitter_screen_name)
            
        except Exception as e:
            raise serializers.ValidationError(dict(error=e))

        return dict(success=True)

    def save_twitter_user(self, user, access_token, access_token_secret, user_twitter_id,
        twitter_name, twitter_screen_name) -> None:
        twitter_user = Twitter.objects.filter(
            access_token=access_token, access_secret=access_token_secret)
        
        if twitter_user:
            raise serializers.ValidationError("twitter account already use another user")
        else:
            twitter = Twitter(
                user = user,
                access_token = access_token,
                access_secret = access_token_secret,
                user_twitter_id = user_twitter_id,
                twitter_name = twitter_name,
                twitter_screen_name = twitter_screen_name
            )

            twitter.save()

class TwitterMessageSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True)
    message = serializers.CharField()
    pause = serializers.BooleanField(write_only=True, required=False)

    def validate(self, attrs):
        user_id = attrs.get("user_id")
        message = attrs.get("message")
        
        if not message:
            raise serializers.ValidationError("message must be required!")
        
        user = User.objects.filter(id=user_id).first()

        if not hasattr(user, "twitter"):
            raise serializers.ValidationError("user must add twitter account to save message")

        return attrs

    def create(self, validated_data):
        user_id = validated_data.get("user_id")
        message = validated_data.get("message")
        pause = validated_data.get("pause", False)
        user = User.objects.filter(id=user_id).first()

        if not hasattr(user.twitter, "direct_message"):
            direct_message = TwitterMessage(
                twitter=user.twitter,             
                message=message,
                pause = pause
            )
            direct_message.save()
            create_scheduler_job(direct_message.id, direct_message.send_direct_messages, "twitter")
        else:
            dm = user.twitter.direct_message
            dm.message = message
            if pause:
                dm.pause = pause
            dm.save()

        return dict(message=message, pause=pause)

class RedditUrlSerializer(serializers.Serializer):
    
    def validate(self, attrs):
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        redirect_url = os.environ.get("FRONTEND_URL")
        redirect_url = redirect_url + "/account"
        user_agent = "onlygrow-ben-app"

        reddit = self.get_auth(client_id, client_secret, redirect_url, user_agent)
        url = self.get_url(reddit) 

        return dict(url=url)
    
    def get_auth(self, client_id, client_secret, redirect_url, user_agent):
        reddit = praw.Reddit(
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = redirect_url,
            user_agent = user_agent
        )
        return reddit
    
    def get_url(self, reddit):
        state = "reddit-" + "".join(random.choices(string.ascii_lowercase, k=30))
        scopes = ["submit","edit","identity","modflair","modposts","flair","read","privatemessages",
        "modnote","modcontributors","modmail","modconfig","subscribe","structuredstyles","vote",
        "wikiedit","mysubreddits","modlog","save","modothers","adsconversions","report","account",
        "modtraffic","wikiread","modwiki","modself","history"]
        url = reddit.auth.url(scopes, state, "permanent")
        return url

class SaveRedditUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True)
    code = serializers.CharField(write_only=True)

    def validate(self, attrs):
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        redirect_url = os.environ.get("FRONTEND_URL")
        redirect_url = redirect_url + "/account"
        user_agent = "onlygrow-ben-app"
        user_id = attrs.get("user_id")

        try:
            user = User.objects.get(pk=user_id)

            code = attrs.get('code')
            reddit = praw.Reddit(
                client_id = client_id,
                client_secret = client_secret,
                redirect_uri = redirect_url,
                user_agent = user_agent
            )
            refresh_token = reddit.auth.authorize(code=code)
            user_reddit = reddit.user.me()
            user_reddit_name = user_reddit.name

            self.save_reddit_user(user=user, user_reddit_name=user_reddit_name,
                refresh_token=refresh_token)

        except Exception as e:
            raise serializers.ValidationError(dict(error=e))

        return dict(success=True)

    def save_reddit_user(self, user, user_reddit_name, refresh_token) -> None:
        reddit_user = Reddit.objects.filter(user_reddit_name=user_reddit_name)
        if reddit_user:
            raise serializers.ValidationError("reddit account already use another user")
        else:
            reddit = Reddit(
                user = user,
                user_reddit_name = user_reddit_name,
                refresh_token = refresh_token
            )

            reddit.save()

class RedditMessageSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True)
    message = serializers.CharField()
    pause = serializers.BooleanField(write_only=True, required=False)

    def validate(self, attrs):
        user_id = attrs.get("user_id")
        message = attrs.get("message")
        
        if not message:
            raise serializers.ValidationError("message must be required!")

        user = User.objects.filter(id=user_id).first()

        if not hasattr(user, "reddit"):
            raise serializers.ValidationError("user must add reddit account to save message")

        return attrs

    def create(self, validated_data):
        user_id = validated_data.get("user_id")
        message = validated_data.get("message")
        pause = validated_data.get("pause", False)
        user = User.objects.filter(id=user_id).first()

        if not hasattr(user.reddit, "direct_message"):
            direct_message = RedditMessage(
                reddit=user.reddit,             
                message=message,
                pause = pause
            )
            direct_message.save()
            create_scheduler_job(direct_message.id, direct_message.send_direct_messages, "reddit")
        else:
            dm = user.reddit.direct_message
            dm.message = message
            if pause:
                dm.pause = pause
            dm.save()

        return dict(message=message, pause=pause)
