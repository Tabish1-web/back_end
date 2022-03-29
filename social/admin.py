from django.contrib import admin
from .models import (
    Reddit, Twitter, TwitterMessage,
    TwitterMessageSender, RedditMessage,
    RedditMessageSender)

admin.site.register(Reddit)
admin.site.register(RedditMessage)
admin.site.register(RedditMessageSender)
admin.site.register(Twitter)
admin.site.register(TwitterMessage)
admin.site.register(TwitterMessageSender)
