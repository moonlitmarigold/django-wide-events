from .Base import Collector

class User(Collector):

    def on_create(self, request):

        event_user = {}

        if hasattr(request, "user"):
            event_user["id"] = request.user.id
            event_user["username"] = request.user.username
            event_user["is_authenticated"] = request.user.is_authenticated
            event_user["is_staff"] = request.user.is_staff
            event_user["is_superuser"] = request.user.is_superuser
            event_user["is_anonymous"] = request.user.is_anonymous

        if event_user:
            self.set(user=event_user)

