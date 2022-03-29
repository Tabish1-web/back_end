from django.urls import path
from .views import (
    SaveMediaView,SaveTweetStatusView, SaveRedditView,
    GetTwitterView, GetRedditView
)

urlpatterns = [
    path("save/media", SaveMediaView.as_view(), name="save-tweet-media"),
    path("twitter/tweet", SaveTweetStatusView.as_view(), name="save-tweet"),
    path("reddit/post", SaveRedditView.as_view(), name="save-reddit"),
    path("get/twitter/tweets", GetTwitterView.as_view(), name="get-tweets"),
    path("get/reddit/posts", GetRedditView.as_view(), name="get-reddits"),
]