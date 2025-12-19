import logging
from typing import Optional

from mymodule.common.usecases.base import BaseUseCase
from mymodule.hello.domain.entities.person import Person
from mymodule.hello.domain.services.greetings import GreetingsService


class SayHelloUseCase(BaseUseCase):
    def __init__(self, greetings_service: GreetingsService, person: Person):
        super().__init__()

        self._greetings_service = greetings_service
        self._person = person
        self._result = None

    @property
    def result(self) -> Optional[str]:
        return self._result

    def execute(self):
        logging.info("Running say hello use case")
        self._result = self._greetings_service.say_hello_to(self._person)
