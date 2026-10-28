from rest_framework.routers import SimpleRouter

from .views import NoteViewSet

router = SimpleRouter()
router.register("test-notes", NoteViewSet, basename="test-note")

urlpatterns = router.urls
