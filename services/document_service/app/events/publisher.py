from libs.service_common.messaging import (
    EventMessage,
    EventPublisher,
    EventSubscriber,
    InMemoryTopicBroker,
    RabbitMQTopicPublisher,
    RabbitMQTopicSubscriber,
)

HistoryEventMessage = EventMessage
HistoryEventPublisher = EventPublisher
HistoryEventSubscriber = EventSubscriber


class InMemoryHistoryEventPublisher(InMemoryTopicBroker):
    pass


class RabbitMQHistoryEventPublisher(RabbitMQTopicPublisher):
    pass


class RabbitMQHistoryEventSubscriber(RabbitMQTopicSubscriber):
    pass
