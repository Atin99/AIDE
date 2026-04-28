import unittest

from rag.agent import lookup_for_reasoning
from rag.retriever import rag_available, retrieve


class RagModuleTests(unittest.TestCase):
    def test_lookup_for_reasoning_degrades_gracefully_without_index(self):
        value = lookup_for_reasoning("marine stainless steel pitting resistance")
        self.assertIsInstance(value, str)

    def test_retrieve_returns_list_when_rag_is_unavailable(self):
        if rag_available():
            self.assertIsInstance(retrieve("titanium fatigue", n_results=2), list)
        else:
            self.assertEqual(retrieve("titanium fatigue", n_results=2), [])


if __name__ == "__main__":
    unittest.main()
