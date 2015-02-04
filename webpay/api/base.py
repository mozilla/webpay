from rest_framework import permissions


class BuyerIsLoggedIn(permissions.IsAuthenticated):
    """
    Grants view access if the buyer has logged in.

    This includes logging in through Firefox Accounts
    explicitly or implicitly.
    """

    def has_permission(self, request, view):
        return bool(request.session.get('uuid'))
