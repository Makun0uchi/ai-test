from libs.service_common.messaging import (
    EventMessage,
    EventPublisher,
    InMemoryTopicBroker,
    RabbitMQTopicPublisher,
)

HospitalEventMessage = EventMessage
HospitalEventPublisher = EventPublisher


class InMemoryHospitalEventPublisher(InMemoryTopicBroker):
    pass


class RabbitMQHospitalEventPublisher(RabbitMQTopicPublisher):
    pass
