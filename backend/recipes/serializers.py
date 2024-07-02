from rest_framework import serializers
from django.shortcuts import get_object_or_404

from django.db.models import F
from users.serializers import CustomUserSerializer
from recipes.models import (
    Tags, Ingredients, Recipes, RecipesIngredients,
)
from django.core.files.base import ContentFile
import base64


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
    # id = serializers.ReadOnlyField(source="ingredient.id")
    # name = serializers.ReadOnlyField(source="ingredient.name")
    # unit_of_measurement = serializers.ReadOnlyField(
    #     source="ingredient.measurement_unit"
    # )

    class Meta:
        model = RecipesIngredients
        fields = '__all__'


class RecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов"""

    author = CustomUserSerializer(read_only=True)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField()

    # def get_ingredients(self, obj):
    #     ingredients = RecipesIngredients.objects.filter(recipe=obj)
    #     serializer = IngredientsSerializer(many=True)

    #     return serializer.data

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipesingredients__amount')
        )
        return ingredients

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
        )


class CreateRecipesIngredientsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    # id = serializers.ReadOnlyField(source='ingredient.id')
    # name = serializers.ReadOnlyField(source="ingredient.name")
    # unit_of_measurement = serializers.ReadOnlyField(
    #     source="ingredient.measurement_unit"
    # )

    class Meta:
        model = RecipesIngredients
        fields = ('id', 'amount')


class CreateRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецептов"""

    ingredients = CreateRecipesIngredientsSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tags.objects.all(), many=True
    )

    class Meta:
        model = Recipes
        fields = '__all__'
        # fields = ('id', 'tags', 'name', 'cooking_time')

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(**validated_data)
        # for tag in tags:
        #     recipes_tags.objects.create(recipe=recipe, tag=tag)
        recipe.tags.set(tags)
        print(ingredients)
        for ingredient in ingredients:
            # ingredient_id = ingredient.get('id')
            # pk=ingredient.get['id']
            # print(pk)
            ingredient_obj = get_object_or_404(
                Ingredients.objects.all(), pk=ingredient.get('id')
            )
            # print(ingredient_obj)
            amount = ingredient.get('amount')
            RecipesIngredients.objects.create(
                recipe=recipe, ingredient=ingredient_obj, amount=amount
            )
        return recipe

    # def create(self, validated_data):
    #     tags = validated_data.pop('tags')
    #     ingredients = validated_data.pop('ingredients')

    #     recipe = Recipes.objects.create(**validated_data)
    #     recipe.tags.set(tags)

    #     # for ingredient in ingredients:
    #     #     amount = ingredient['amount']
    #     #     ingredient = Ingredients.objects.get(pk=ingredient['id'])

    #     #     RecipesIngredients.objects.create(
    #     #         recipe=recipe, ingredient=ingredient, amount=amount
    #     #     )

    #     recipe_ingredients = [
    #         RecipesIngredients(
    #             recipe=recipe,
    #             ingredient=ingredient_data['id'],
    #             amount=ingredient_data['amount']
    #         ) for ingredient_data in ingredients
    #     ]
    #     RecipesIngredients.objects.bulk_create(recipe_ingredients)

    #     return recipe

    # def create(self, validated_data):
    #     # Уберём список достижений из словаря validated_data и сохраним его
    #     tags = validated_data.pop('tags')

    #     # Создадим нового котика пока без достижений, данных нам достаточно
    #     recipe = Recipes.objects.create(**validated_data)
    #     recipe.tags.set(tags)

    #     return recipe

    def to_representation(self, instance):
        return RecipesSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    image = serializers.CharField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')
