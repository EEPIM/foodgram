from django.core.files.base import ContentFile
from django.db.models import F
from django.shortcuts import get_object_or_404
import base64
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from recipes.models import (
    Tags, Ingredients, Recipes, RecipesIngredients,
)
from users.serializers import CustomUserSerializer


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class TagsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tags
        fields = ('id', 'name', 'slug')


class IngredientsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredients
        fields = '__all__'


class RecipesIngredientsSerializer(serializers.ModelSerializer):

    class Meta:
        model = RecipesIngredients
        fields = '__all__'


class RecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов"""

    author = CustomUserSerializer(read_only=True)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipesingredients__amount')
        )
        return ingredients

    def get_is_favorited(self, instance):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=instance).exists()

    def get_is_in_shopping_cart(self, instance):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.shopping_cart.filter(recipe=instance).exists()

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

    def validate_ingredients(self, value):
        if len(value) == 0:
            raise ValidationError('Нужен хотя бы один ингредиент!')
        ingrediens_list = []
        for val in value:
            try:
                ingredient = Ingredients.objects.get(id=val['id'])
            except Ingredients.DoesNotExist:
                raise serializers.ValidationError('Ингредиент не найден!')
            if ingredient in ingrediens_list:
                raise ValidationError('Ингредиент не должны повторятся!')
            ingrediens_list.append(ingredient)
            if val['amount'] <= 0:
                raise ValidationError(
                    'Количество ингредиента должно быть больше 0!'
                )
        return value

    def validate_tags(self, value):
        if len(value) == 0:
            raise ValidationError('Нужен хотя бы один тег!')
        tag_list = []
        for val in value:
            if val in tag_list:
                raise ValidationError('Тег не должен повторятся!')
            tag_list.append(val)
        return value

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            ingredient_obj = get_object_or_404(
                Ingredients.objects.all(), pk=ingredient_id
            )
            amount = ingredient.get('amount')
            RecipesIngredients.objects.create(
                recipe=recipe, ingredient=ingredient_obj, amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })
        if 'tags' not in validated_data:
            raise ValidationError({
                'tags': 'Нужен хотя бы один тег!'
            })
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        for ingredient in ingredients:
            RecipesIngredients.objects.create(
                recipe=instance,
                ingredient=get_object_or_404(
                    Ingredients.objects.all(), pk=ingredient['id']
                ),
                amount=ingredient['amount']
            )
        instance.tags.clear()
        instance.tags.set(tags)
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipesSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    image = serializers.CharField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')
