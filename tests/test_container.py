"""Tests for PolInjectumContainer."""

import unittest
from abc import ABC, abstractmethod

from polinjectum.exceptions import RegistrationError, ResolutionError
from polinjectum.lifecycle import Lifecycle
from polinjectum.polinjectum_container import PolInjectumContainer


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
