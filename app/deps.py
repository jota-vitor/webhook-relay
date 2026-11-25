from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.task_queue import DeliveryQueue, get_queue

DbSession = Annotated[Session, Depends(get_db)]
Queue = Annotated[DeliveryQueue, Depends(get_queue)]


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


PageParams = Annotated[Pagination, Depends()]
