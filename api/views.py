# views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from utils.s3 import *
from .models import Profile, Post, Comment, Like , Follow, Notification
from .serializers import (
    UserSerializer,
    CommentSerializer,
    ProfileSerializer,
    PostSerializer,
    NotificationSerializer
)

User = get_user_model()


# Auth Views
@api_view(['POST'])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=request.data.get('password')
        )
        Profile.objects.create(user=user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        print(str(e))
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, username=None):
        user = request.user if username is None else get_object_or_404(User, username=username)
        profile = get_object_or_404(Profile, user=user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request, username):
        user = get_object_or_404(User, username=username)
        profile = get_object_or_404(Profile, user=user)


        avatar = request.FILES.get('avatar', None)
        if avatar:
            file_name = f"avatars/{user.username}/{os.path.basename(avatar.name)}"
            file_url = upload_to_s3(avatar, file_name)
            profile.avatar_url = file_url


        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        posts = Post.objects.all().order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)


class PostDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, post_id):
        return get_object_or_404(Post, id=post_id)

    def get(self, request, post_id):
        post = self.get_object(post_id)
        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data)

    def put(self, request, post_id):
        post = self.get_object(post_id)
        if post.user != request.user:
            return Response({"detail": "You don't have permission to edit this post."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, post_id):
        post = self.get_object(post_id)
        if post.user != request.user:
            return Response({"detail": "You don't have permission to edit this post."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_id):
        post = self.get_object(post_id)
        if post.user != request.user:
            return Response({"detail": "You don't have permission to delete this post."},
                            status=status.HTTP_403_FORBIDDEN)

        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class UserPostsView(APIView):
    def get(self, request, username=None):
        user = request.user if username is None else get_object_or_404(User, username=username)
        posts = Post.objects.filter(user=user).order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, username=None):
        user = request.user if username is None else get_object_or_404(User, username=username)
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostCommentsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_post(self, post_id):
        return get_object_or_404(Post, id=post_id)

    def get(self, request, post_id):
        post = self.get_post(post_id)
        comments = Comment.objects.filter(post=post)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, post_id):
        post = self.get_post(post_id)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            add_comment_notification(request, post_id)
            serializer.save(user=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, comment_id):
        return get_object_or_404(Comment, id=comment_id)

    def get(self, request, post_id, comment_id):
        comment = self.get_object(comment_id)
        if comment.post.id != post_id:
            return Response({"detail": "Comment does not belong to this post"},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = CommentSerializer(comment)
        return Response(serializer.data)

    def put(self, request, post_id, comment_id):
        comment = self.get_object(comment_id)
        if comment.post.id != post_id:
            return Response({"detail": "Comment does not belong to this post"},
                            status=status.HTTP_400_BAD_REQUEST)
        if comment.user != request.user:
            return Response({"detail": "You don't have permission to edit this comment."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CommentSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, post_id, comment_id):
        comment = self.get_object(comment_id)
        post = get_object_or_404(Post, id=post_id)
        if comment.post.id != post_id:
            return Response({"detail": "Comment does not belong to this post"},
                            status=status.HTTP_400_BAD_REQUEST)
        if comment.user != request.user and post.user != request.user:
            return Response({"detail": "You don't have permission to delete this comment."},
                            status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikePostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):

        post = get_object_or_404(Post, id=post_id)


        like, created = Like.objects.get_or_create(user=request.user, post=post)

        if not created:

            return Response({'message': 'Вы уже поставили лайк этому посту'}, status=status.HTTP_200_OK)


        post.likes_count = post.likes.count()
        post.save()
        like_post_notification(request, post)

        serializer = PostSerializer(post, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)


        try:
            like = Like.objects.get(user=request.user, post=post)
            like.delete()


            post.likes_count = post.likes.count()
            post.save()


            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data)
        except Like.DoesNotExist:
            return Response({'message': 'Вы не ставили лайк этому посту'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user(request, username):
    try:
        to_follow = User.objects.get(username=username)
        if request.user == to_follow:
            return Response({'error': 'You cannot follow yourself.'}, status=400)

        created = Follow.objects.get_or_create(follower=request.user, following=to_follow)
        follow_user_notification(request, username)
        if created:
            return Response({'message': 'Successfully followed.'}, status=201)
        else:
            return Response({'message': 'Already following.'}, status=200)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unfollow_user(request, username):
    try:
        to_unfollow = User.objects.get(username=username)
        follow = Follow.objects.filter(follower=request.user, following=to_unfollow)
        if follow.exists():
            follow.delete()
            return Response({'message': 'Unfollowed successfully.'})
        else:
            return Response({'message': 'You are not following this user.'}, status=400)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_following_status(request, username):
    try:
        user_to_check = User.objects.get(username=username)
        is_following = Follow.objects.filter(follower=request.user, following=user_to_check).exists()
        return Response({'is_following': is_following})
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)



class SearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')

        users = User.objects.filter(username__icontains=query)


        posts = Post.objects.filter(content__icontains=query)


        profile_data = ProfileSerializer(Profile.objects.filter(user__in=users), many=True).data
        user_data = {user['id']: user for user in profile_data}  # Создаём словарь с user_id как ключами

        post_data = PostSerializer(posts, many=True, context={'request': request}).data


        for post in post_data:
            user_profile = user_data.get(post['user']['id'])
            if user_profile:
                post['user_profile'] = user_profile

        return Response({
            'users': user_data,
            'posts': post_data
        }, status=status.HTTP_200_OK)


def like_post_notification(request, post_id):
    post = Post.objects.get(id=post_id)
    if post.user != request.user:
        Notification.objects.create(
            recipient=post.user,
            sender=request.user,
            message=" лайкнул ваш пост"
        )

def add_comment_notification(request, post_id):
    post = Post.objects.get(id=post_id)
    if request.method == "POST":
        if post.user != request.user:
            Notification.objects.create(
                recipient=post.user,
                sender=request.user,
                message="прокомментировал ваш пост"
            )

def follow_user_notification(request, username):
    target_user = User.objects.get(username=username)
    if target_user != request.user:
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            message=" подписался на вас"
        )

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).order_by('-created_at')
        qs.update(is_read=True)
        return qs

class ProfileListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles, many=True)
        return Response(serializer.data)


def health_check(request):
    return JsonResponse({'status': 'ok'}, status=200)