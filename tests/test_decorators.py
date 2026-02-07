"""Tests for @injectable and @inject decorators."""

import unittest
from abc import ABC, abstractmethod

from polinjectum.decorators import inject, injectable
from polinjectum.exceptions import RegistrationError
from polinjectum.lifecycle import Lifecycle
from polinjectum.polinjectum_container import PolInjectumContainer


class TestInjectableBare(unittest.TestCase):
    """@injectable used without arguments."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_registers_class_under_itself(self) -> None:
        @injectable
        class Repo:
            pass

        instance = PolInjectumContainer().get_me(Repo)
        self.assertIsInstance(instance, Repo)

    def test_returns_original_class(self) -> None:
        @injectable
        class Svc:
            pass

        self.assertEqual(Svc.__name__, "Svc")

    def test_default_lifecycle_is_singleton(self) -> None:
        @injectable
        class Single:
            pass

        container = PolInjectumContainer()
        self.assertIs(container.get_me(Single), container.get_me(Single))


class TestInjectableWithArgs(unittest.TestCase):
    """@injectable(...) used with keyword arguments."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_registers_under_specified_interface(self) -> None:
        class Animal(ABC):
            @abstractmethod
            def speak(self) -> str: ...

        @injectable(interface=Animal)
        class Dog(Animal):
            def speak(self) -> str:
                return "woof"

        result = PolInjectumContainer().get_me(Animal)
        self.assertIsInstance(result, Dog)
        self.assertEqual(result.speak(), "woof")

    def test_qualifier(self) -> None:
        class Logger:
            def __init__(self) -> None:
                self.name = "base"

        @injectable(interface=Logger, qualifier="file")
        class FileLogger(Logger):
            def __init__(self) -> None:
                self.name = "file"

        result = PolInjectumContainer().get_me(Logger, qualifier="file")
        self.assertEqual(result.name, "file")

    def test_transient_lifecycle(self) -> None:
        @injectable(lifecycle=Lifecycle.TRANSIENT)
        class Request:
            pass

        container = PolInjectumContainer()
        a = container.get_me(Request)
        b = container.get_me(Request)
        self.assertIsNot(a, b)

    def test_returns_original_class(self) -> None:
        @injectable(lifecycle=Lifecycle.TRANSIENT)
        class Temp:
            pass

        self.assertEqual(Temp.__name__, "Temp")
        self.assertTrue(callable(Temp))


class TestInjectableAutoWiring(unittest.TestCase):
    """@injectable classes that depend on other injectables."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_auto_wires_injectable_dependencies(self) -> None:
        @injectable
        class Repository:
            pass

        @injectable
        class Service:
            def __init__(self, repo: Repository) -> None:
                self.repo = repo

        service = PolInjectumContainer().get_me(Service)
        self.assertIsInstance(service.repo, Repository)


class TestInjectableOnFunction(unittest.TestCase):
    """@injectable used on functions/methods as factory registration."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_registers_under_return_type(self) -> None:
        class Database:
            def __init__(self, url: str):
                self.url = url

        @injectable
        def create_database() -> Database:
            return Database("postgresql://localhost/mydb")

        result = PolInjectumContainer().get_me(Database)
        self.assertIsInstance(result, Database)
        self.assertEqual(result.url, "postgresql://localhost/mydb")

    def test_returns_original_function(self) -> None:
        class Svc:
            pass

        @injectable
        def create_svc() -> Svc:
            return Svc()

        self.assertEqual(create_svc.__name__, "create_svc")
        self.assertTrue(callable(create_svc))

    def test_factory_with_extra_parameters_and_defaults(self) -> None:
        class HttpClient:
            def __init__(self, base_url: str, timeout: float):
                self.base_url = base_url
                self.timeout = timeout

        @injectable
        def create_client() -> HttpClient:
            return HttpClient("https://api.example.com", timeout=30.0)

        client = PolInjectumContainer().get_me(HttpClient)
        self.assertEqual(client.base_url, "https://api.example.com")
        self.assertEqual(client.timeout, 30.0)

    def test_factory_with_auto_wired_deps_and_extra_params(self) -> None:
        @injectable
        class Logger:
            def __init__(self) -> None:
                self.name = "app"

        class Service:
            def __init__(self, logger: Logger, retries: int):
                self.logger = logger
                self.retries = retries

        @injectable
        def create_service(logger: Logger) -> Service:
            return Service(logger, retries=3)

        service = PolInjectumContainer().get_me(Service)
        self.assertIsInstance(service.logger, Logger)
        self.assertEqual(service.retries, 3)

    def test_with_explicit_interface(self) -> None:
        class Sender(ABC):
            @abstractmethod
            def send(self) -> str: ...

        class SmtpSender(Sender):
            def __init__(self, host: str):
                self.host = host

            def send(self) -> str:
                return f"smtp://{self.host}"

        @injectable(interface=Sender)
        def create_sender() -> SmtpSender:
            return SmtpSender("mail.example.com")

        result = PolInjectumContainer().get_me(Sender)
        self.assertIsInstance(result, SmtpSender)
        self.assertEqual(result.send(), "smtp://mail.example.com")

    def test_with_qualifier(self) -> None:
        class Cache:
            def __init__(self, backend: str):
                self.backend = backend

        @injectable(interface=Cache, qualifier="redis")
        def create_redis_cache() -> Cache:
            return Cache("redis://localhost:6379")

        @injectable(interface=Cache, qualifier="memory")
        def create_memory_cache() -> Cache:
            return Cache("memory://")

        container = PolInjectumContainer()
        redis = container.get_me(Cache, qualifier="redis")
        memory = container.get_me(Cache, qualifier="memory")
        self.assertEqual(redis.backend, "redis://localhost:6379")
        self.assertEqual(memory.backend, "memory://")

    def test_with_transient_lifecycle(self) -> None:
        class Request:
            pass

        @injectable(lifecycle=Lifecycle.TRANSIENT)
        def create_request() -> Request:
            return Request()

        container = PolInjectumContainer()
        a = container.get_me(Request)
        b = container.get_me(Request)
        self.assertIsNot(a, b)

    def test_no_return_annotation_raises(self) -> None:
        with self.assertRaises(RegistrationError) as ctx:
            @injectable
            def bad_factory():
                return "oops"

        self.assertIn("return type annotation", str(ctx.exception))

    def test_no_return_annotation_with_explicit_interface_ok(self) -> None:
        @injectable(interface=str)
        def no_hint_factory():
            return "works"

        result = PolInjectumContainer().get_me(str)
        self.assertEqual(result, "works")

    def test_singleton_is_default_for_functions(self) -> None:
        class Token:
            pass

        @injectable
        def create_token() -> Token:
            return Token()

        container = PolInjectumContainer()
        self.assertIs(container.get_me(Token), container.get_me(Token))


class TestInject(unittest.TestCase):
    """@inject decorator for functions."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_resolves_missing_args_from_container(self) -> None:
        class Greeter:
            def greet(self) -> str:
                return "hello"

        self.container.meet(Greeter)

        @inject
        def say_hello(g: Greeter) -> str:
            return g.greet()

        self.assertEqual(say_hello(), "hello")

    def test_caller_supplied_args_take_precedence(self) -> None:
        class Num:
            def __init__(self) -> None:
                self.value = 10

        self.container.meet(Num)

        @inject
        def get_value(n: Num) -> int:
            return n.value

        custom = Num()
        custom.value = 99
        self.assertEqual(get_value(custom), 99)

    def test_caller_supplied_kwargs_take_precedence(self) -> None:
        class Config:
            def __init__(self) -> None:
                self.debug = False

        self.container.meet(Config)

        @inject
        def is_debug(cfg: Config) -> bool:
            return cfg.debug

        custom = Config()
        custom.debug = True
        self.assertEqual(is_debug(cfg=custom), True)

    def test_skips_unannotated_params(self) -> None:
        @inject
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)

    def test_skips_unregistered_types(self) -> None:
        class Unknown:
            pass

        @inject
        def needs_unknown(u: Unknown) -> str:
            return "got it"

        with self.assertRaises(TypeError):
            needs_unknown()

    def test_preserves_function_metadata(self) -> None:
        @inject
        def my_func() -> None:
            """My docstring."""
            pass

        self.assertEqual(my_func.__name__, "my_func")
        self.assertEqual(my_func.__doc__, "My docstring.")


if __name__ == "__main__":
    unittest.main()
