from app.models.application import TimelineEvent
from app.services.repositories.interfaces import TimelineEventRepository
from app.services import storage_service as store


class JsonTimelineEventRepository(TimelineEventRepository):
    def save(self, event: TimelineEvent) -> None:
        store.save_timeline_event(event)

    def list_by_application(self, application_id: str) -> list[TimelineEvent]:
        return store.list_timeline_events(application_id)
