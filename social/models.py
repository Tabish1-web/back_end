from django.db import models
from django.contrib.auth import get_user_model
import os
import tweepy
import praw

# import asyncio

User = get_user_model()

class TwitterMessage(models.Model):
    twitter = models.OneToOneField("Twitter", on_delete=models.CASCADE,
        null=False, blank=False, related_name="direct_message")
    message = models.TextField(null=True, blank=True)
    pause = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.twitter.twitter_name

    @property
    def get_direct_messages_ids(self):
        dms = self.twitter.twitter_api.get_direct_messages()
        dm_ids = [dm.message_create.get('sender_id') for dm in dms]
        db_dms = self.senders.filter(sender__in=dm_ids).values("sender")
        db_dms = [dm['sender'] for dm in db_dms]
        dms = list((set(dm_ids) ^ set(db_dms)))
        user = self.twitter.twitter_api.get_user(
            screen_name=self.twitter.twitter_screen_name)
        twitter_user_id = user.id_str
        dms = list(filter(lambda x : x != twitter_user_id, dms))
        return dms

    def send_direct_messages(self) -> None:
        obj = TwitterMessage.objects.get(pk=self.pk)
        if obj.pause:
            return
        api = obj.twitter.twitter_api
        for send_id in obj.get_direct_messages_ids:
            try:
                obj.senders.create(sender=send_id)
                api.send_direct_message(recipient_id=send_id, text=obj.message)
            except:
                pass
        
class TwitterMessageSender(models.Model):
    twitter_message = models.ForeignKey(TwitterMessage, on_delete=models.CASCADE,
        null=False, blank=False, related_name="senders")
    sender = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self) -> str:
        return self.sender

class Twitter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, 
        null=False, blank=False, related_name="twitter")
    user_twitter_id = models.BigIntegerField(null=False, blank=False)
    twitter_name = models.CharField(max_length=255)
    twitter_screen_name = models.CharField(max_length=100)
    access_token = models.CharField(max_length=555)
    access_secret = models.CharField(max_length=555)

    @property
    def twitter_api(self):
        consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
        consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
        access_token = self.access_token
        access_secret = self.access_secret

        auth = tweepy.OAuth1UserHandler(
            consumer_key = consumer_key,
            consumer_secret = consumer_secret,
            access_token = access_token,
            access_token_secret = access_secret
        )

        api = tweepy.API(auth)

        return api

    def __str__(self) -> str:
        return self.user.username

class RedditMessage(models.Model):
    reddit = models.OneToOneField("Reddit", on_delete=models.CASCADE,
        null=False, blank=False, related_name="direct_message")
    message = models.TextField(null=True, blank=True)
    pause = models.BooleanField(default=False)

    @property
    def get_redditor_name(self):
        user = self.reddit.reddit_api.user.me()
        reddit_username = user.name
        return reddit_username
    
    @property
    def get_messages_author(self):
        reddit = self.reddit.reddit_api
        dms = reddit.inbox.unread()
        dm_ids = [dm.author.name for dm in dms]
        db_dms = self.senders.filter(sender__in=dm_ids).values("sender")
        db_dms = [dm['sender'] for dm in db_dms]
        dms = list((set(dm_ids) ^ set(db_dms)))
        reddit_username = self.get_redditor_name 
        dms = list(filter(lambda x : x != reddit_username, dms))
        return dms

    def send_direct_messages(self) -> None:
        obj = RedditMessage.objects.get(pk=self.pk)
        if obj.pause:
            return
        api = obj.reddit.reddit_api
        for name in obj.get_messages_author:
            try:
                obj.senders.create(sender=name)
                redditor = api.redditor(name=name)
                redditor.message(obj.get_redditor_name, obj.message)  
            except:
                pass

        print('DOne #####')

    def __str__(self) -> str:
        return self.reddit.user_reddit_name

class RedditMessageSender(models.Model):
    reddit_message = models.ForeignKey(RedditMessage, on_delete=models.CASCADE,
        null=False, blank=False, related_name="senders")
    sender = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self) -> str:
        return self.sender

class Reddit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        null=False, blank=False, related_name="reddit")
    user_reddit_name = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=555)
    
    @property
    def reddit_api(self):
        
        api = praw.Reddit(
            client_id = os.environ.get("REDDIT_CLIENT_ID"),
            client_secret = os.environ.get("REDDIT_CLIENT_SECRET"),
            refresh_token = self.refresh_token,
            user_agent = "onlygrow-ben-app"
        )

        return api

    def __str__(self) -> str:
        return self.user.username

class Instagram(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
        null=False, blank=False, related_name="instagram")
    