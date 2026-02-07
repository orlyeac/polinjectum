"""Tests for polinjectum custom exceptions."""

import unittest

from polinjectum.exceptions import RegistrationError, ResolutionError


class TestRegistrationError(unittest.TestCase):
    def test_can_be_raised_and_caught(self) -> None:
        with self.assertRaises(RegistrationError):
            raise RegistrationError("bad registration")

    def test_message_is_preserved(self) -> None:
        err = RegistrationError("duplicate key")
        self.assertEqual(str(err), "duplicate key")

    def test_is_an_exception(self) -> None:
        self.assertTrue(issubclass(RegistrationError, Exception))


class TestResolutionError(unittest.TestCase):
    def test_can_be_raised_and_caught(self) -> None:
        with self.assertRaises(ResolutionError):
            raise ResolutionError("not found")

    def test_message_without_chain(self) -> None:
        err = ResolutionError("missing dep")
        self.assertEqual(str(err), "missing dep")
        self.assertEqual(err.chain, [])

    def test_message_with_chain(self) -> None:
        err = ResolutionError("cannot resolve", chain=["A", "B", "C"])
        self.assertIn("A -> B -> C", str(err))
        self.assertEqual(err.chain, ["A", "B", "C"])

    def test_is_an_exception(self) -> None:
        self.assertTrue(issubclass(ResolutionError, Exception))


if __name__ == "__main__":
    unittest.main()
