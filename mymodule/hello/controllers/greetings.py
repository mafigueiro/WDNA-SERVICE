from mymodule.hello.domain.entities.person import Person
from mymodule.hello.domain.services.greetings import GreetingsService
from mymodule.hello.usecases.say_hello import SayHelloUseCase


class GreetingsController:
    def __init__(self) -> None:
        self._greetings_service = GreetingsService()

    def say_hello_to(self, name: str) -> list[str]:
        person = Person(name=name)
        uc = SayHelloUseCase(self._greetings_service, person)
        uc.execute()

        return uc.result
