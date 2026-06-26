from uuid import UUID as uuid_default

from sqlalchemy.orm import DeclarativeBase
from uuid_utils import uuid4


def generate_uuid():
    return uuid_default(str(uuid4))


class Base(DeclarativeBase):
	pass
