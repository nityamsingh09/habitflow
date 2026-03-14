from django.urls import path
from . import views

urlpatterns = [
    path('api/challenges',                                views.challenge_list,      name='challenge_list'),
    path('api/challenges/create',                         views.create_challenge,    name='create_challenge'),
    path('api/challenges/my-invites',                     views.my_invites,          name='my_invites'),
    path('api/challenges/<int:challenge_id>',             views.challenge_detail,    name='challenge_detail'),
    path('api/challenges/<int:challenge_id>/join',        views.join_challenge,      name='join_challenge'),
    path('api/challenges/<int:challenge_id>/decline',     views.decline_challenge,   name='decline_challenge'),
    path('api/challenges/<int:challenge_id>/log',         views.log_challenge,       name='log_challenge'),
    path('api/challenges/<int:challenge_id>/invite',      views.invite_to_challenge, name='invite_challenge'),
    path('api/challenges/<int:challenge_id>/invites',     views.challenge_invites,   name='challenge_invites'),
]
