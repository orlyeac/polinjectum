"""Tests for PolInjectumContainer."""

import unittest
from abc import ABC, abstractmethod
from typing import Annotated

from polinjectum.exceptions import RegistrationError, ResolutionError
from polinjectum.lifecycle import Lifecycle
from polinjectum.polinjectum_container import PolInjectumContainer, Qualifier


class TestContainerSingleton(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_same_instance_returned(self) -> None:
        c1 = PolInjectumContainer()
        c2 = PolInjectumContainer()
        self.assertIs(c1, c2)

    def test_reset_creates_new_instance(self) -> None:
        c1 = PolInjectumContainer()
        PolInjectumContainer.reset()
        c2 = PolInjectumContainer()
        self.assertIsNot(c1, c2)


class TestMeetAndGetMe(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_register_and_resolve(self) -> None:
        self.container.meet(str, factory_function=lambda: "hello")
        self.assertEqual(self.container.get_me(str), "hello")

    def test_resolve_unregistered_raises(self) -> None:
        with self.assertRaises(ResolutionError):
            self.container.get_me(int)

    def test_factory_defaults_to_interface(self) -> None:
        self.container.meet(list)
        result = self.container.get_me(list)
        self.assertEqual(result, [])

    def test_non_callable_factory_raises(self) -> None:
        with self.assertRaises(RegistrationError):
            self.container.meet(str, factory_function=42)  # type: ignore[arg-type]


class TestDuplicateRegistration(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_duplicate_raises(self) -> None:
        self.container.meet(str, factory_function=lambda: "first")
        with self.assertRaises(RegistrationError) as ctx:
            self.container.meet(str, factory_function=lambda: "second")
        self.assertIn("Duplicate registration for str", str(ctx.exception))

    def test_duplicate_with_qualifier_raises(self) -> None:
        self.container.meet(str, qualifier="x", factory_function=lambda: "first")
        with self.assertRaises(RegistrationError) as ctx:
            self.container.meet(str, qualifier="x", factory_function=lambda: "second")
        self.assertIn("str[x]", str(ctx.exception))

    def test_same_base_different_qualifiers_allowed(self) -> None:
        self.container.meet(str, qualifier="a", factory_function=lambda: "alpha")
        self.container.meet(str, qualifier="b", factory_function=lambda: "beta")
        self.assertEqual(self.container.get_me(str, qualifier="a"), "alpha")
        self.assertEqual(self.container.get_me(str, qualifier="b"), "beta")


class TestAmbiguousResolution(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_single_qualified_resolves_without_qualifier(self) -> None:
        self.container.meet(str, qualifier="only", factory_function=lambda: "found")
        self.assertEqual(self.container.get_me(str), "found")

    def test_multiple_qualified_raises_ambiguous(self) -> None:
        self.container.meet(str, qualifier="a", factory_function=lambda: "alpha")
        self.container.meet(str, qualifier="b", factory_function=lambda: "beta")
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(str)
        self.assertIn("Ambiguous resolution for str", str(ctx.exception))
        self.assertIn("'a'", str(ctx.exception))
        self.assertIn("'b'", str(ctx.exception))

    def test_default_registration_takes_precedence(self) -> None:
        self.container.meet(str, factory_function=lambda: "default")
        self.container.meet(str, qualifier="q", factory_function=lambda: "qualified")
        self.assertEqual(self.container.get_me(str), "default")


class TestQualifiers(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_different_qualifiers_different_instances(self) -> None:
        self.container.meet(str, qualifier="a", factory_function=lambda: "alpha")
        self.container.meet(str, qualifier="b", factory_function=lambda: "beta")
        self.assertEqual(self.container.get_me(str, qualifier="a"), "alpha")
        self.assertEqual(self.container.get_me(str, qualifier="b"), "beta")

    def test_qualifier_none_is_default(self) -> None:
        self.container.meet(int, factory_function=lambda: 42)
        self.assertEqual(self.container.get_me(int), 42)
        self.assertEqual(self.container.get_me(int, qualifier=None), 42)


class TestLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_singleton_returns_same_instance(self) -> None:
        self.container.meet(
            list,
            factory_function=list,
            lifecycle=Lifecycle.SINGLETON,
        )
        a = self.container.get_me(list)
        b = self.container.get_me(list)
        self.assertIs(a, b)

    def test_transient_returns_new_instance(self) -> None:
        self.container.meet(
            list,
            factory_function=list,
            lifecycle=Lifecycle.TRANSIENT,
        )
        a = self.container.get_me(list)
        b = self.container.get_me(list)
        self.assertIsNot(a, b)

    def test_singleton_is_default_lifecycle(self) -> None:
        self.container.meet(dict, factory_function=dict)
        a = self.container.get_me(dict)
        b = self.container.get_me(dict)
        self.assertIs(a, b)


class TestGetMeList(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_returns_all_implementations(self) -> None:
        self.container.meet(int, qualifier="a", factory_function=lambda: 1)
        self.container.meet(int, qualifier="b", factory_function=lambda: 2)
        self.container.meet(int, factory_function=lambda: 3)
        result = sorted(self.container.get_me_list(int))
        self.assertEqual(result, [1, 2, 3])

    def test_empty_when_nothing_registered(self) -> None:
        self.assertEqual(self.container.get_me_list(float), [])


class TestAutoWiring(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_auto_wires_constructor_dependencies(self) -> None:
        class Repository:
            pass

        class Service:
            def __init__(self, repo: Repository) -> None:
                self.repo = repo

        self.container.meet(Repository)
        self.container.meet(Service)

        service = self.container.get_me(Service)
        self.assertIsInstance(service, Service)
        self.assertIsInstance(service.repo, Repository)

    def test_auto_wire_failure_raises_resolution_error(self) -> None:
        class Missing:
            pass

        class NeedsMissing:
            def __init__(self, dep: Missing) -> None:
                self.dep = dep

        self.container.meet(NeedsMissing)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(NeedsMissing)
        self.assertIn("Missing", str(ctx.exception))

    def test_parameters_with_defaults_are_skipped(self) -> None:
        class OptionalDeps:
            def __init__(self, value: int = 10) -> None:
                self.value = value

        self.container.meet(OptionalDeps)
        obj = self.container.get_me(OptionalDeps)
        self.assertEqual(obj.value, 10)

    def test_parameters_without_annotations_are_skipped(self) -> None:
        self.container.meet(dict, factory_function=lambda x=5: {"x": x})
        result = self.container.get_me(dict)
        self.assertEqual(result, {"x": 5})


class TestQualifierAutoWiring(unittest.TestCase):
    """Auto-wiring with Annotated[Type, Qualifier("name")]."""

    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_annotated_qualifier_resolves_correct_registration(self) -> None:
        class Cache:
            def __init__(self, backend: str):
                self.backend = backend

        self.container.meet(Cache, qualifier="redis", factory_function=lambda: Cache("redis"))
        self.container.meet(Cache, qualifier="memory", factory_function=lambda: Cache("memory"))

        class Service:
            def __init__(self, cache: Annotated[Cache, Qualifier("redis")]) -> None:
                self.cache = cache

        self.container.meet(Service)
        service = self.container.get_me(Service)
        self.assertEqual(service.cache.backend, "redis")

    def test_annotated_qualifier_different_params_different_qualifiers(self) -> None:
        class Logger:
            def __init__(self, name: str):
                self.name = name

        self.container.meet(Logger, qualifier="file", factory_function=lambda: Logger("file"))
        self.container.meet(Logger, qualifier="console", factory_function=lambda: Logger("console"))

        class App:
            def __init__(
                self,
                file_log: Annotated[Logger, Qualifier("file")],
                console_log: Annotated[Logger, Qualifier("console")],
            ) -> None:
                self.file_log = file_log
                self.console_log = console_log

        self.container.meet(App)
        app = self.container.get_me(App)
        self.assertEqual(app.file_log.name, "file")
        self.assertEqual(app.console_log.name, "console")

    def test_annotated_without_qualifier_resolves_default(self) -> None:
        class Repo:
            pass

        self.container.meet(Repo)

        class Service:
            def __init__(self, repo: Annotated[Repo, "some metadata"]) -> None:
                self.repo = repo

        self.container.meet(Service)
        service = self.container.get_me(Service)
        self.assertIsInstance(service.repo, Repo)

    def test_missing_qualified_registration_raises(self) -> None:
        class Store:
            pass

        class NeedsStore:
            def __init__(self, s: Annotated[Store, Qualifier("missing")]) -> None:
                self.s = s

        self.container.meet(NeedsStore)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(NeedsStore)
        self.assertIn("Store[missing]", str(ctx.exception))

    def test_mixed_plain_and_annotated_params(self) -> None:
        class DbConn:
            pass

        class Cache:
            def __init__(self, backend: str):
                self.backend = backend

        self.container.meet(DbConn)
        self.container.meet(Cache, qualifier="redis", factory_function=lambda: Cache("redis"))

        class Service:
            def __init__(
                self,
                db: DbConn,
                cache: Annotated[Cache, Qualifier("redis")],
            ) -> None:
                self.db = db
                self.cache = cache

        self.container.meet(Service)
        service = self.container.get_me(Service)
        self.assertIsInstance(service.db, DbConn)
        self.assertEqual(service.cache.backend, "redis")


class TestQualifierClass(unittest.TestCase):
    def test_repr(self) -> None:
        q = Qualifier("redis")
        self.assertEqual(repr(q), "Qualifier('redis')")

    def test_equality(self) -> None:
        self.assertEqual(Qualifier("a"), Qualifier("a"))
        self.assertNotEqual(Qualifier("a"), Qualifier("b"))

    def test_hash(self) -> None:
        self.assertEqual(hash(Qualifier("a")), hash(Qualifier("a")))
        s = {Qualifier("x"), Qualifier("x"), Qualifier("y")}
        self.assertEqual(len(s), 2)


class TestCircularDependency(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()
        self.container = PolInjectumContainer()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_direct_cycle(self) -> None:
        class B:
            pass

        class A:
            def __init__(self, b: B) -> None:
                self.b = b

        def b_init(self, a: A) -> None:
            self.a = a
        B.__init__ = b_init

        self.container.meet(A)
        self.container.meet(B)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(A)
        self.assertIn("Circular dependency", str(ctx.exception))

    def test_self_dependency(self) -> None:
        class Ouroboros:
            pass

        def ouro_init(self, me: Ouroboros) -> None:
            self.me = me
        Ouroboros.__init__ = ouro_init

        self.container.meet(Ouroboros)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(Ouroboros)
        self.assertIn("Circular dependency", str(ctx.exception))
        self.assertIn("Ouroboros", str(ctx.exception))

    def test_transitive_cycle(self) -> None:
        class X:
            pass

        class Y:
            pass

        class Z:
            def __init__(self, x: X) -> None:
                self.x = x

        def x_init(self, y: Y) -> None:
            self.y = y
        X.__init__ = x_init

        def y_init(self, z: Z) -> None:
            self.z = z
        Y.__init__ = y_init

        self.container.meet(X)
        self.container.meet(Y)
        self.container.meet(Z)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(X)
        self.assertIn("Circular dependency", str(ctx.exception))

    def test_error_message_shows_chain(self) -> None:
        class Q:
            pass

        class P:
            def __init__(self, q: Q) -> None:
                self.q = q

        def q_init(self, p: P) -> None:
            self.p = p
        Q.__init__ = q_init

        self.container.meet(P)
        self.container.meet(Q)
        with self.assertRaises(ResolutionError) as ctx:
            self.container.get_me(P)
        self.assertIn("P", str(ctx.exception))
        self.assertIn("Q", str(ctx.exception))

    def test_no_false_positive_for_shared_dependency(self) -> None:
        class Shared:
            pass

        class ConsumerA:
            def __init__(self, s: Shared) -> None:
                self.s = s

        class ConsumerB:
            def __init__(self, s: Shared) -> None:
                self.s = s

        class Root:
            def __init__(self, a: ConsumerA, b: ConsumerB) -> None:
                self.a = a
                self.b = b

        self.container.meet(Shared)
        self.container.meet(ConsumerA)
        self.container.meet(ConsumerB)
        self.container.meet(Root)
        root = self.container.get_me(Root)
        self.assertIsInstance(root.a.s, Shared)
        self.assertIsInstance(root.b.s, Shared)


class TestReset(unittest.TestCase):
    def setUp(self) -> None:
        PolInjectumContainer.reset()

    def tearDown(self) -> None:
        PolInjectumContainer.reset()

    def test_reset_clears_registrations(self) -> None:
        container = PolInjectumContainer()
        container.meet(str, factory_function=lambda: "hi")
        PolInjectumContainer.reset()
        container = PolInjectumContainer()
        with self.assertRaises(ResolutionError):
            container.get_me(str)


if __name__ == "__main__":
    unittest.main()
