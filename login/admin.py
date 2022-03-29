from django.contrib import admin
from .models import User
from rest_framework_simplejwt import token_blacklist

admin.site.register(User)

class OutstandingTokenAdmin(token_blacklist.admin.OutstandingTokenAdmin):
    def has_delete_permission(self, *args, **kwargs):
        return True

admin.site.unregister(token_blacklist.models.OutstandingToken) 
admin.site.register(token_blacklist.models.OutstandingToken, OutstandingTokenAdmin)


