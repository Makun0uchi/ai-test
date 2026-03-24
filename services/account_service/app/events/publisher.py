from libs.service_common.messaging import (
    EventMessage,
    EventPublisher,
    InMemoryTopicBroker,
    RabbitMQTopicPublisher,
)

AccountEventMessage = EventMessage
AccountEventPublisher = EventPublisher


class InMemoryAccountEventPublisher(InMemoryTopicBroker):
    pass


class RabbitMQAccountEventPublisher(RabbitMQTopicPublisher):
    pass
