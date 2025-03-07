from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from datetime import datetime, timedelta, timezone

from ..models import SystemNotify, Notify
from ..models.template import NotifyTemplate
from ..tasks import send_notifications_users_mailing_list


@admin.register(NotifyTemplate)
class NotifyTemplateAdmin(admin.ModelAdmin):
    change_form_template = "send_notify.html"
    fields = (
        'title',
        'is_active',
        'subject',
        'is_delete_after',
        'get_context_description',
        'text',
        'html',
        'user',
        'email',
        'phone',
        'telegram_chat_id',
        'viber_chat_id',
        'type',
        'category',
        'event',
        'user_lists',
        'send_at',
    )
    readonly_fields = (
        'get_context_description',
        'get_event_description',
    )
    list_display = ('title', 'is_active', 'type', 'category', 'event', 'user', 'email', 'phone', 'send_at')
    list_filter = ('type', 'category', 'event', 'is_active')
    actions = ['create_mailing', ]
    filter_horizontal = ('user_lists',)
    raw_id_fields = ('user',)

    def create_mailing(self, request, queryset):
        count = Notify.send(event=None, context={}, notify_templates=queryset)
        self.message_user(request, 'Рассылка создана, кол-во сообщений: {}'.format(count))

    create_mailing.short_description = "Сделать рассылку"

    def create_mailing_list(self, request, obj):
        user_list = []
        for elem in obj.user_lists.all():
            user_list.extend(elem.users.all())
        user_list = list(set(user_list))
        list_notify = []
        time = datetime.now(timezone.utc)
        count_mail_hour = int(request.POST["_count_mail_hour"])
        for number in range(len(user_list)):
            list_notify.append(user_list[number].pk)
            if (number + 1) % count_mail_hour == 0 or number == len(user_list) - 1:
                send_notifications_users_mailing_list.apply_async(kwargs={"user_list": list_notify}, eta=time)
                time += timedelta(hours=1)
                list_notify = []

    def response_change(self, request, obj):
        context = obj.get_test_data()
        template = obj
        user = obj.user if obj.user else request.user
        if obj.user_lists and "_send_now" in request.POST:
            instance = Notify.objects.create(
                subject=obj.render_subject(template.subject),
                text=obj.render_text(context),
                html=obj.render_html(context),
                user=user,
                email=obj.email,
                type=obj.type,
                category=obj.category,
            )
            instance.start_send()
            self.message_user(request, 'Тестовое уведомление отправлено', level=messages.SUCCESS)
            return HttpResponseRedirect(".")
        elif "_send_now_system" in request.POST:
            instance = SystemNotify.objects.create(
                title=template.subject if template.subject or template.subject != '' else template.title,
                event=template.event,
                user=user,
                data_json=context,
                room_name=f'room_{user.pk}'
            )
            instance.send_notification()
            self.message_user(request, 'Тестовое уведомление отправлено', level=messages.SUCCESS)
            return HttpResponseRedirect(".")

        if obj.user_lists and "_newsletter" in request.POST:
            self.create_mailing_list(request, obj)
            self.message_user(request, 'Рассылка началась', level=messages.SUCCESS)
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)

    def get_changelist(self, request, **kwargs):
        events_message = NotifyTemplate.get_blank_events_message()
        if events_message:
            self.message_user(request, events_message, level=messages.WARNING)
        return super().get_changelist(request, **kwargs)
