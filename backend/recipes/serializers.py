from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
import base64
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from recipes.models import (
    Tags, Ingredients, Recipes, RecipesIngredients, Favorite, ShoppingCart
)
from users.serializers import CustomUserSerializer


class Base64ImageField(serializers.ImageField):
    """Сериализатор для картинок"""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор тегов"""

    class Meta:
        model = Tags
        fields = ('id', 'name', 'slug')


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов"""

    class Meta:
        model = Ingredients
        fields = '__all__'


class RecipesIngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор для связи рецептов и индредиентов"""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipesIngredients
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов"""

    author = CustomUserSerializer(read_only=True)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    def get_ingredients(self, obj):
        ingredients = RecipesIngredients.objects.filter(recipe=obj)
        serializer = RecipesIngredientsSerializer(ingredients, many=True)
        return serializer.data

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
        model = Recipes
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
    """Вспомогательный сериализатор для связи рецептов и индредиентов"""
    id = serializers.IntegerField()

    class Meta:
        model = RecipesIngredients
        fields = ('id', 'amount')


class CreateRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""

    author = CustomUserSerializer(read_only=True)
    ingredients = CreateRecipesIngredientsSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tags.objects.all(), many=True
    )
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipes
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
            raise ValidationError('Нужно добавить хотя бы один ингридиент!')
        if not data.get('tags'):
            raise ValidationError('Нужно добавить хотя бы один тег!')

        ingredients_list = data['ingredients']
        ingredients = []

        for ingredient in ingredients_list:
            if not Ingredients.objects.filter(id=ingredient['id']).exists():
                raise ValidationError('Такого ингредиента нет!')
            ingredients.append(ingredient['id'])

        for ingredient in ingredients:
            if ingredients.count(ingredient) > 1:
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

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            amount = ingredient.get('amount')
            ingredient_obj = get_object_or_404(
                Ingredients.objects.all(), pk=ingredient.get('id')
            )
            RecipesIngredients.objects.create(
                recipe=recipe, ingredient=ingredient_obj, amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)

        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        for ingredient in ingredients:
            RecipesIngredients.objects.create(
                recipe=instance,
                ingredient=get_object_or_404(
                    Ingredients.objects.all(), pk=ingredient.get('id')
                ),
                amount=ingredient['amount']
            )
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipesSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации рецептов"""

    image = serializers.CharField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')
