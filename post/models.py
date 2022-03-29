from django.db import models
from django.contrib.auth import get_user_model
from rest_framework import serializers

import os
import tweepy
import praw

from praw.models import InlineGif, InlineImage, InlineVideo, Submission

User = get_user_model()

class Media(models.Model):
    tweet = models.OneToOneField("TwitterPost", on_delete=models.CASCADE,
        null=True, blank=True, related_name="media")
    reddit = models.OneToOneField("RedditPost", on_delete=models.CASCADE,
        null=True, blank=True, related_name="media")
    media_type = models.CharField(max_length=10, null=True, blank=True)
    media_id = models.BigIntegerField(null=True, blank=True)
    file = models.FileField(upload_to="uploads/media")

    def __str__(self) -> str:
        return self.media_type

class TwitterPost(models.Model):
    POST_CHOICES = (
        ('P', 'Pending'),
        ('C', 'Completed')
    ) 
    user = models.ForeignKey(User, on_delete=models.CASCADE,
        null=False, blank=False, related_name="twitter_posts")
    tweet_id = models.IntegerField(null=True, blank=True)
    reply_id = models.IntegerField(null=True, blank=True)
    tweet = models.TextField(unique=True)
    comment = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=POST_CHOICES, default='C')
    favorite_count = models.IntegerField(null=True, blank=True)
    retweet_count = models.IntegerField(null=True, blank=True)
    truncated = models.BooleanField(default=False)
    post_time = models.DateTimeField(null=False, blank=False)
    update_at = models.DateTimeField(auto_now=True)
    
    @property
    def twitter_api(self):
        api = self.user.twitter.twitter_api
        return api
    
    @property
    def twitter_update_status(self):
        api = self.twitter_api
        
        media_ids = []

        if hasattr(self, "media"):
            media_ids.append(self.media.media_id)
        
        try:
            new_tweet = api.update_status(
                status=self.tweet,
                media_ids = media_ids
            )
        except Exception as e:
            self.delete()
            raise serializers.ValidationError(str(e))

        self.tweet_id = new_tweet.id
        self.save()
        return new_tweet
    
    @property
    def media_upload(self):
        if hasattr(self, "media"):
            api = self.twitter_api
            media = self.media
            filename = media.file.path
            media_id = api.media_upload(
                filename=filename,
                chunked=True
            )
            media.media_id = media_id.media_id
            media.save()

    @property
    def tweet_reply(self) -> None:
        if self.comment:
            api = self.twitter_api
            reply = api.update_status(
                status=self.comment,
                in_reply_to_status_id=self.tweet_id
            )

            self.reply_id = reply.id
            self.save()

        # get analytics data
        self.get_analytics_data
    
    @property
    def delete_tweet(self) -> None:
        if self.tweet_id:
            try:
                self.twitter_api.destroy_status(self.tweet_id)
                self.twitter_api.destroy_status(self.reply_id)
            except Exception as e:
                pass

    @property
    def get_analytics_data(self):
        if self.tweet_id:
            try:
                status = self.twitter_api.get_status(self.tweet_id)
                self.favorite_count = status.favorite_count
                self.retweet_count = status.retweet_count
                self.truncated = status.truncated
                self.save()
            except Exception as e:
                pass

    def __str__(self) -> str:
        return self.user.username
        
class RedditPost(models.Model):
    POST_CHOICES = (
        ('P', 'Pending'),
        ('C', 'Completed')
    ) 
    user = models.ForeignKey(User, on_delete=models.CASCADE,
        null=False, blank=False, related_name="reddit_posts")
    reddit_id = models.CharField(max_length=20 ,null=True, blank=True)
    reply_id = models.CharField(max_length=20, null=True, blank=True)
    title = models.CharField(max_length=555)
    sub_reddit = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    nsfw = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=POST_CHOICES, default='C')
    approved = models.BooleanField(default=False)
    comments_count = models.IntegerField(null=True, blank=False)
    locked = models.BooleanField(default=False)
    saved = models.BooleanField(default=False)
    spam = models.BooleanField(default=False)
    view_count = models.IntegerField(default=False)
    upvote_ratio = models.FloatField(null=True, blank=True)
    awards_received = models.IntegerField(null=True, blank=True)
    spoiler = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    post_time = models.DateTimeField(null=False, blank=False)
    update_at = models.DateTimeField(auto_now=True)

    @property 
    def reddit_api(self):
        api = self.user.reddit.reddit_api
        return api
    
    @property
    def submit_post(self):

        media_ = {}

        # select inline media for reddit (image, video, gif)
        if hasattr(self, "media"):
            media = self.media
            filepath = media.file.path
            if media.media_type == "image":
                media_['image1'] = InlineImage(filepath)
                self.body += "{"+"image1"+"}"
            elif media.media_type == "video":
                    media_['video1'] = InlineVideo(filepath)
                    self.body += "{"+"video1"+"}"
            else:
                media_['gif1'] = InlineGif(filepath)
                self.body += "{"+"gif1"+"}" 
        
        reddit = None
        
        # submit reddit post
        try:
            # add sub reddit on api
            api = self.reddit_api.subreddit(self.sub_reddit)
            
            # submit post on reddit
            reddit = api.submit(
                title=self.title, selftext=self.body or "", url=self.link,
                nsfw=self.nsfw, inline_media=media_)
            
            # comment on reddit post
            comment = None
            if self.comment:
                comment = reddit.reply(self.comment) if self.comment else None
            if reddit.id:
                self.reddit_id = reddit.id
            if comment and comment.id:
                self.reply_id = comment.id
            
            # save on model
            self.save()
            
            # get analytics data
            self.get_analytics_data
                
        except Exception as e:
            self.delete()
            raise serializers.ValidationError(str(e))

        return reddit
    
    @property
    def delete_reddit(self) -> None:
        if self.reddit_id:
            try:
                reddit = self.reddit_api
                reddit = reddit.submission(self.reddit_id)
                reddit.delete()
            except Exception as e:
                raise serializers.ValidationError(str(e))

    @property
    def edit_reddit(self) -> None:
        if self.reddit_id:
            try:
                reddit = self.reddit_api
                submission = reddit.submission(self.reddit_id)
                submission.edit(self.body)
                comment = reddit.comment(self.reply_id)
                comment.edit(self.comment)
            except Exception as e:
                raise serializers.ValidationError(str(e))
    
    @property
    def get_analytics_data(self):
        if self.reddit_id:
            try:
                reddit = self.reddit_api
                submission = reddit.submission(self.reddit_id)
                self.approved = submission.approved
                self.comments_count = int(submission.num_comments)
                self.locked = submission.locked
                self.view_count = 0 and int(submission.view_count)
                self.upvote_ratio = float(submission.upvote_ratio)
                self.awards_received = int(submission.total_awards_received)
                self.spoiler = submission.spoiler
                self.score = int(submission.score)
                self.save()
                
            except Exception as e:
                pass

    def __str__(self) -> str:
        return self.title    
