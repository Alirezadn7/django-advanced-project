from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        
        # Read permissions are allowed to any request
        # always allow GET , HEAD or OPTIONS requests
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow write/delete permissions only to the author of the post
        return obj.author == request.user