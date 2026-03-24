from .base import Base
from .hospital import Hospital, HospitalRoom
from .outbox import HospitalOutbox

__all__ = ["Base", "Hospital", "HospitalOutbox", "HospitalRoom"]
