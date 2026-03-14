from django.urls import path
from . import views

urlpatterns = [
    path('social/',                         views.social_page,           name='social'),

    # Leaderboard & feed
    path('api/leaderboard',                 views.leaderboard,           name='leaderboard'),
    path('api/feed',                        views.feed,                  name='feed'),
    path('api/feed/global',                 views.global_feed,           name='global_feed'),

    # Reactions & comments
    path('api/events/<int:event_id>/react', views.toggle_reaction,       name='toggle_reaction'),
    path('api/events/<int:event_id>/comment',views.add_comment,          name='add_comment'),
    path('api/comments/<int:comment_id>',   views.delete_comment,        name='delete_comment'),

    # Follow
    path('api/follow',                      views.toggle_follow,         name='toggle_follow'),

    # Friends
    path('api/friends',                     views.friends_list,          name='friends_list'),
    path('api/friends/requests',            views.pending_requests,      name='pending_requests'),
    path('api/friends/send',                views.send_friend_request,   name='send_friend_request'),
    path('api/friends/respond',             views.respond_friend_request,name='respond_friend_request'),
    path('api/friends/remove',              views.remove_friend,         name='remove_friend'),

    # Profiles
    path('api/profile',                     views.my_profile_api,        name='my_profile'),
    path('api/users/search',                views.search_users,          name='search_users'),
    path('api/users/<str:username>',        views.public_profile,        name='public_profile'),

    # Chat
    path('api/chat/global',                views.global_chat_messages, name='global_chat'),
    path('api/chat/dm/<uuid:friend_id>',   views.direct_messages,      name='direct_messages'),
    path('api/chat/inbox',                 views.dm_inbox,             name='dm_inbox'),

    # Friends list for invite modal
    path('api/friends/list',               views.friends_for_invite,   name='friends_for_invite'),
]
