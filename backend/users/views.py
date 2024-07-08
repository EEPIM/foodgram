from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import MyUser, Follow
from users.serializers import (
    CustomUserSerializer,
    CustomUserCreateSerializer,
    FollowSerializer,
    CustomUserAvatarSerializer,
)


class CustomUserViewSet(UserViewSet):

    serializer_class = CustomUserCreateSerializer
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        print(self.action)
        if self.action in ('list', 'retrieve'):
            return CustomUserSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action == 'me':
            return CustomUserSerializer
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'subscribe':
            return FollowSerializer

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()

    @action(methods=['put', 'delete'], detail=True)
    def avatar(self, request, **kwargs):
        user = get_object_or_404(MyUser, username=request.user)
        if request.method == 'PUT':
            serializers = CustomUserAvatarSerializer(user, data=request.data)
            if serializers.is_valid():
                serializers.save()
                return Response(serializers.data, status=status.HTTP_200_OK)
            return Response(serializers.errors, status=400)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True
    )
    def subscribe(self, request, **kwargs):
        user = request.user
        author = get_object_or_404(MyUser, id=self.kwargs['id'])
        if request.method == 'POST':
            if Follow.objects.filter(follower=user, author=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого автора', code=400
                )
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя', code=400
                )
            serializer = FollowSerializer(
                author,
                context={"request": request, }
            )
            Follow.objects.create(follower=user, author=author)
            return Response(serializer.data, status=201)
        if request.method == 'DELETE':
            try:
                subscribe = Follow.objects.get(follower=user, author=author)
                subscribe.delete()
            except Follow.DoesNotExist:
                raise serializers.ValidationError('Not Found', code=400)
            return Response(status=204)

    @action(
        methods=['get', ],
        detail=False,
    )
    def subscriptions(self, request):
        user = request.user
        queryset = MyUser.objects.filter(author__follower=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
