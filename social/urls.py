from django.urls import path
from .views import (
    DeleteRedditUserView,
    RedditURLView, 
    SaveRedditUserView, 
    DeleteTwitterUserView,
    TwitterURLView, 
    SaveTwitterUserView,
    DeleteRedditUserView,
    TwitterMessageView,
    RedditMessageView
)



urlpatterns = [
    path("twitter/url", TwitterURLView.as_view(), name="twitter-url"),
    path("save/twitter/user", SaveTwitterUserView.as_view(), name="save-twitter-user"),
    path("delete/twitter/user", DeleteTwitterUserView.as_view(), name="delete-twitter-user"),
    path("save/twitter/message", TwitterMessageView.as_view(), name="save-twitter-message"),
    path("reddit/url", RedditURLView.as_view(), name="reddit-url"),
    path("save/reddit/user", SaveRedditUserView.as_view(), name="save-reddit-user"),
    path("delete/reddit/user", DeleteRedditUserView.as_view(), name="delete-reddit-user"),
    path("save/reddit/message", RedditMessageView.as_view(), name="save-reddit-message"),
]