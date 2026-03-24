from libs.service_common.messaging import (
    EventMessage,
    EventPublisher,
    InMemoryTopicBroker,
    RabbitMQTopicPublisher,
)

TimetableEventMessage = EventMessage
TimetableEventPublisher = EventPublisher


class InMemoryTimetableEventPublisher(InMemoryTopicBroker):
    pass


class RabbitMQTimetableEventPublisher(RabbitMQTopicPublisher):
    pass
