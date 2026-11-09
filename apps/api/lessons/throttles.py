from rest_framework.throttling import SimpleRateThrottle


class LessonCreateRateThrottle(SimpleRateThrottle):
    """Lesson creation per signed-in user, across all IPs."""

    scope = "lesson_create"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
