from django.contrib import admin
from .models import RedditPost, TwitterPost, Media

admin.site.register(Media)
admin.site.register(TwitterPost)
admin.site.register(RedditPost)
