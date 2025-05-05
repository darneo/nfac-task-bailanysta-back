from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    register,
    logout,
    ProfileView,
    PostListView,
    PostDetailView,
    UserPostsView,
    PostCommentsView,
    CommentDetailView,
    LikePostView,
    follow_user,
    unfollow_user,
    check_following_status,
    SearchView, NotificationListView, ProfileListView
)

urlpatterns = [
    path('auth/register/', register, name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', logout, name='logout'),

    path('search/', SearchView.as_view(), name='search'),


    path('profile/<str:username>/', ProfileView.as_view(), name='user-profile'),
    path('profile/<str:username>/posts/', UserPostsView.as_view(), name='user-posts'),
    path('follow/<str:username>/', follow_user, name='follow-user'),
    path('unfollow/<str:username>/', unfollow_user, name='unfollow-user'),
    path('following-status/<str:username>/', check_following_status , name='check-following-status'),
    path('posts/',  PostListView.as_view(), name='posts-list'),
    path('posts/<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),

    path('notifications/', NotificationListView.as_view(), name='notification-list'),

    path('posts/<int:post_id>/comments/', PostCommentsView.as_view(), name='post-comments'),
    path('posts/<int:post_id>/comments/<int:comment_id>/', CommentDetailView.as_view(), name='comment-detail'),
    path('users/', ProfileListView.as_view(), name='user-list'),
]