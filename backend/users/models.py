# from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

# User = get_user_model()


class MyUser(AbstractUser):

    email = models.EmailField(
        max_length=254,
        unique=True,
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=(RegexValidator(r'^[\w.@+-]+\Z'),),
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    avatar = models.ImageField(
        upload_to='users/images/',
        null=True,
        default=None
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name", "password",]

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):

    follower = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        null=True,
        related_name='follower')

    author = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        null=True,
        related_name='author')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'author'],
                name='unique_following'
            )
        ]

    def __str__(self):
        return f'{self.follower} - {self.author}'
