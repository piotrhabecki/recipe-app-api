"""
Tests for the Ingredients API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, User, Recipe

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='test@example.com', password='testpass123'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user: User, name: str):
    """Create and return a sample ingredient"""
    ingredient = Ingredient.objects.create(user=user, name=name)
    return ingredient


def detail_url(ingredient_id):
    """Create and return a ingredient detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagIngredientTests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com', password='testpass123')
        self.client.force_authenticate(self.user)

    def test_retrive_ingredients(self):
        """Test retrieving a list of tags."""
        create_ingredient(user=self.user, name="Vanilla")
        create_ingredient(user=self.user, name="Peper")
        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_list_limited_to_user(self):
        """Test list of ingredients is limited of authenticated user."""

        other_user = create_user(
            email='other@example.com', password='testpass123')

        create_ingredient(user=other_user, name="Vanila")
        ingredient = create_ingredient(user=self.user, name="Peper")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.filter(user=self.user)
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test updating a ingredient"""

        ingredient = Ingredient.objects.create(user=self.user, name='Test1')

        payload = {'name': 'Test2'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting a tag successful."""
        ingredient = create_ingredient(user=self.user, name="Orange")

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients assigned to recipes"""
        in1 = Ingredient.objects.create(user=self.user, name='Ingredient1')
        in2 = Ingredient.objects.create(user=self.user, name='Ingredient2')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'))
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients return a unique list"""
        ing = Ingredient.objects.create(user=self.user, name='Ingredient 1')
        Ingredient.objects.create(user=self.user, name='Ingredient 2')
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Recipe 1',
            time_minutes=5,
            price=Decimal('4.50'))

        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Recipe 2',
            time_minutes=5,
            price=Decimal('4.50'))

        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
