from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer, UserCreateSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.fields import Base64ImageField
from recipes.models import (
    Tag, Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart
)
from users.models import Follow

User = get_user_model()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для редактирования пользователя."""

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
        )


class CustomUserSerializer(UserSerializer):
    """Сериализатор для просмотра пользователя"""

    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'avatar',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Follow.objects.filter(
                follower=self.context.get('request').user,
                author=obj.id
            ).exists()
        )


class CustomUserAvatarSerializer(UserSerializer):
    """Сериализатор для аватара пользователя"""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            'avatar',
        )


class FollowSerializer(CustomUserSerializer):
    """Сериализатор для подписок"""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj.id)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.id).count()


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор тегов"""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов"""

    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipesIngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор для связи рецептов и ингредиентов"""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов"""

    author = CustomUserSerializer(read_only=True)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = RecipesIngredientsSerializer(
        many=True, read_only=True, source='recipe_ingredient')

    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    def get_is_favorited(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Favorite.objects.filter(
                user=self.context.get('request').user,
                recipe=obj
            ).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and ShoppingCart.objects.filter(
                user=self.context.get('request').user,
                recipe=obj
            ).exists()
        )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
        )


class CreateRecipesIngredientsSerializer(serializers.ModelSerializer):
    """Вспомогательный сериализатор для связи рецептов и ингредиентов"""
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class CreateRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""

    author = CustomUserSerializer(read_only=True)
    ingredients = CreateRecipesIngredientsSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
            'author'
        )

    def validate(self, data):
        if not data.get('ingredients'):
            raise ValidationError('Нужно добавить хотя бы один ингредиент!')
        if not data.get('tags'):
            raise ValidationError('Нужно добавить хотя бы один тег!')

        ingredients_list = data['ingredients']
        ingredients = []

        for ingredient in ingredients_list:
            if not Ingredient.objects.filter(id=ingredient['id']).exists():
                raise ValidationError('Такого ингредиента нет!')
            ingredients.append(ingredient['id'])
            if ingredients.count(ingredient['id']) > 1:
                raise ValidationError(
                    'Нельзя включать два одинаковых ингредиента!'
                )

        tags_list = data['tags']
        tags = []
        for tag in tags_list:
            if tag in tags:
                raise ValidationError('Нельзя указать два одинаковых тега!')
            tags.append(tag)
        return data

    def bulk_create_update(self, ingredients, recipe):
        ingredient_list = []
        for ingredient in ingredients:
            ingredient_list.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount')
                )
            )
        RecipeIngredient.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.bulk_create_update(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.bulk_create_update(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipesSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации рецептов"""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
