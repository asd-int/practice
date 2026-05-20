from .models import Users

def user_avatar_processor(request):
    user_id = request.session.get('user_id')
    if user_id:
        # Ищем пользователя в базе данных
        user_obj = Users.objects.filter(id=user_id).first()
        if user_obj and user_obj.avatar:
            return {'current_user_avatar': user_obj.avatar.url}
    return {'current_user_avatar': None}