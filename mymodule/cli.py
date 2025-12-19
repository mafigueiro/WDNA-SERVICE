import click

from mymodule.analytics.controllers.analytics import AnalyticsController
from mymodule.common.configuration.config import configure_logging
from mymodule.hello.controllers.greetings import GreetingsController


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx) -> None:  # pylint: disable=unused-argument
    configure_logging()


@main.command("say-hello")
@click.argument("name", type=click.STRING, required=True)
def hello(name: str) -> None:
    controller = GreetingsController()
    result = controller.say_hello_to(name)

    print(result)


@main.command("list-clients")
def list_clients() -> None:
    controller = AnalyticsController()
    result = controller.list_clients()

    print(result)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
