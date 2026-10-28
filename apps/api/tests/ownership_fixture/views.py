from core.viewsets import OwnedModelViewSet

from .models import Note
from .serializers import NoteSerializer


class NoteViewSet(OwnedModelViewSet):
    model = Note
    serializer_class = NoteSerializer
