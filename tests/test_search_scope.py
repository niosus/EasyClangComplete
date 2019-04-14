"""Test search scopes."""
import imp
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.utils import search_scope

imp.reload(search_scope)

TreeSearchScope = search_scope.TreeSearchScope
ListSearchScope = search_scope.ListSearchScope


class test_search_scope(TestCase):
    """Testing file related stuff."""

    def test_init_tree(self):
        """Test if we can init a search path from tree."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        scope = TreeSearchScope(from_folder=current_folder,
                                to_folder=parent_folder)
        self.assertEqual(current_folder, scope.from_folder)
        self.assertEqual(parent_folder, scope.to_folder)

    def test_init_tree_partial(self):
        """Test if we can init a search path from tree."""
        current_folder = path.dirname(path.abspath(__file__))
        scope = TreeSearchScope(from_folder=current_folder)
        self.assertEqual(current_folder, scope.from_folder)
        self.assertEqual(scope.to_folder, search_scope.ROOT_PATH)

    def test_iterate_tree(self):
        """Test if we can init a search path from tree."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        scope = TreeSearchScope(from_folder=current_folder,
                                to_folder=parent_folder)
        self.assertIs(scope, iter(scope))
        self.assertEqual(current_folder, next(scope))
        self.assertEqual(parent_folder, next(scope))
        try:
            next(scope)
            self.fail("Did not throw StopIteration")
        except StopIteration:
            pass

    def test_init_list(self):
        """Test if we can init a search path from list."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        scope = ListSearchScope([current_folder, parent_folder])
        self.assertEqual(current_folder, scope.folders[0])
        self.assertEqual(parent_folder, scope.folders[1])

    def test_iterate_list(self):
        """Test if we can init a search path from list."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        scope = ListSearchScope([current_folder, parent_folder])
        self.assertEqual(current_folder, next(scope))
        self.assertEqual(parent_folder, next(scope))
        try:
            next(scope)
            self.fail("Did not throw StopIteration")
        except StopIteration:
            pass
