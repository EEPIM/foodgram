from django.core.validators import MinValueValidator
from django.db import models

from users.models import MyUser


class Ingredients(models.Model):

    name = models.CharField('Ингредиент', max_length=25,)
    measurement_unit = models.CharField('Единица измерения', max_length=10)

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'

    def __str__(self):
        return self.name


class Tags(models.Model):

    name = models.CharField(max_length=25)
    slug = models.CharField(max_length=25)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipes(models.Model):

    ingredients = models.ManyToManyField(
        Ingredients, through='RecipesIngredients')

    tags = models.ManyToManyField(Tags)
    author = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        blank=True, null=True,
        default=None,
        verbose_name='Изображение'
    )
    name = models.CharField(max_length=200)
    text = models.TextField()
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipesIngredients(models.Model):

    recipe = models.ForeignKey(
        Recipes, on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredients, on_delete=models.PROTECT
    )
    amount = models.IntegerField()

    def __str__(self):
        return f'{self.recipe} {self.ingredient} {self.amount}'


class Favorite(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipes,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт'
    )
