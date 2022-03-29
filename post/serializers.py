from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
from django.conf import settings

from social.utils import get_scheduler
import datetime
import pytz

from .models import Media, RedditPost, TwitterPost

User = get_user_model()

# save post serializers

class SaveMediaSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate(self, attrs):
        file = attrs.get('file')

        filename = file.name.split(".")
        if len(filename) > 2:
            raise serializers.ValidationError(
                detail="filename is not allowed"
            )
        _, ext = filename
        type = self.check_extension(ext)
        attrs['media_type'] = type
         
        return attrs

    def check_extension(self, extension):
        image_extensions = settings.IMAGE_FILE_FORMATS
        video_extensions = settings.VIDEO_FILE_FORMATS
        other_extensions = settings.OTHER_FILE_FORMATS
        media_type = None
        if extension in image_extensions:
            media_type = "image"
        elif extension in video_extensions:
            media_type = "video"
        elif extension in other_extensions:
            media_type = "other"
        else:
            raise serializers.ValidationError(
                detail="file extension not allowed"
            )
        return media_type

    def create(self, validated_data):
        media = Media.objects.create(**validated_data)
        return dict(media_id=media.id)

class SaveTweetStatusSerializer(serializers.Serializer):
    user = serializers.IntegerField(write_only=True)
    tweet = serializers.CharField(write_only=True,validators=[UniqueValidator(queryset=TwitterPost.objects.all())])
    comment = serializers.CharField(write_only=True, required=False)
    mediaId = serializers.IntegerField(write_only=True, required=False)
    postOn = serializers.IntegerField(write_only=True, required=False)

    def validate(self, attrs):
        user = attrs.get("user")
        tweet = attrs.get("tweet")

        if not tweet:
            raise serializers.ValidationError("tweet must be include text")

        attrs["user_id"] = user
        attrs.pop("user")
        
        return attrs

    def create(self, validated_data):
       
        # set post time
        post_time = validated_data.get("postOn")
        current_time = datetime.datetime.now(tz=pytz.UTC)
        post_time = post_time and datetime.datetime.fromtimestamp(post_time,tz=pytz.UTC)
        validated_data['post_time'] = post_time or current_time
        post_time and validated_data.pop('postOn')

        # get media from model
        media_id = validated_data.get("mediaId")
        media = Media.objects.filter(id=media_id).first()
        media_id and validated_data.pop('mediaId')
        
        # create twitter post
        twitter = TwitterPost.objects.create(**validated_data) 
        
        # save media of twitter
        if media:
            media.tweet = twitter
            media.save()

        # save status on pending 
        if post_time:
            twitter.status = "P"
            twitter.save()

        # post on twitter now
        (not post_time and not twitter.get_status_display() == "Pending"
            and self.create_twitter_post(twitter=twitter))

        # post on twitter schedule later
        scheduler = get_scheduler()
        (post_time and twitter.get_status_display() == "Pending" and
            scheduler.add_job(
                self.create_twitter_post, "date", 
                id=f"tweet-{twitter.id}", run_date=twitter.post_time, 
                args=[twitter]))
        scheduler.start()

        return dict(success=True)

    def create_twitter_post(self, twitter):
        twitter.status = "C"
        twitter.media_upload
        twitter.twitter_update_status
        twitter.tweet_reply
        twitter.save()

class SaveRedditSerializer(serializers.Serializer):
    user = serializers.IntegerField(write_only=True)
    title = serializers.CharField(write_only=True)
    sub_reddit = serializers.CharField(write_only=True)
    link = serializers.URLField(write_only=True, required=False)
    body = serializers.CharField(write_only=True, required=False)
    nsfw = serializers.BooleanField(write_only=True, default=False)
    comment = serializers.CharField(write_only=True, required=False)
    mediaId = serializers.IntegerField(write_only=True, required=False)
    postOn = serializers.IntegerField(write_only=True, required=False)

    def validate(self, attrs):
        user = attrs.get("user")
        title = attrs.get("title")
        sub_reddit = attrs.get("sub_reddit")

        if not title:
            raise serializers.ValidationError("title must be include text")

        if not sub_reddit:
            raise serializers.ValidationError("sub_reddit must be needed")

        attrs["user_id"] = user
        attrs.pop("user")
        
        return attrs

    def create(self, validated_data):
        
        # set post time
        post_time = validated_data.get("postOn")
        current_time = datetime.datetime.now(tz=pytz.UTC)
        post_time = post_time and datetime.datetime.fromtimestamp(post_time,tz=pytz.UTC)
        validated_data['post_time'] = post_time or current_time
        post_time and validated_data.pop('postOn')
        
        # get media from model
        media_id = validated_data.get("mediaId")
        media = Media.objects.filter(id=media_id).first()
        media_id and validated_data.pop('mediaId')

        # create reddit post
        reddit = RedditPost.objects.create(**validated_data)

        # save media of reddit 
        if media: 
            media.reddit = reddit
            media.save()
        
        # save status on pending 
        if post_time:
            reddit.status = "P"
            reddit.save()
        
        # post on reddit now
        (not post_time and not reddit.get_status_display() == "Pending"
            and self.create_reddit_post(reddit=reddit))

        # post on reddit schedule later
        scheduler = get_scheduler()
        (post_time and reddit.get_status_display() == "Pending" and
            scheduler.add_job(self.create_reddit_post, "date", 
            id=f"post-{reddit.id}",run_date=reddit.post_time, 
            args=[reddit]))
        scheduler.start()

        return dict(success=True)

    def create_reddit_post(self, reddit):
        reddit.status = "C"
        reddit.submit_post
        reddit.save()

# end save post serializers

# get post serializers

class GetMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ["media_type", "file"]

class GetTwitterSerializer(serializers.ModelSerializer):
    media = GetMediaSerializer(many=False, read_only=True)
    class Meta:
        model = TwitterPost
        fields = ["id","favorite_count","comment","media","post_time","retweet_count",
            "status","truncated","tweet"]

class GetRedditSerializer(serializers.ModelSerializer):
    media = GetMediaSerializer(many=False, read_only=True)
    class Meta:
        model = RedditPost
        fields = ["id","approved","awards_received","body","comment","comments_count",
            "locked","media","post_time","score","spoiler","status","title",
            "upvote_ratio","view_count"]