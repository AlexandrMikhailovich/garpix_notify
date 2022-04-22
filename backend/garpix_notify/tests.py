import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
django.setup()

import random
import string

from unittest import TestCase

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Notify
from .models import NotifyCategory
from .models import NotifyTemplate
from .models import NotifyUserList
from .models import NotifyUserListParticipant
from .models.choices import TYPE

User = get_user_model()


def random_char(char_num):
    return ''.join(random.choice(string.ascii_letters) for _ in range(char_num))


class PreBuildTestCase(TestCase):
    def setUp(self):
        # нулевой евент, только для теста
        self.PASS_TEST_EVENT = 0
        # тестовый пользователь
        self.data_user = {
            'username': 'email_test' + random_char(4),
            'email': 'test@garpix.com',
            'password': 'BlaBla123',
            'first_name': 'Ivan',
            'last_name': 'Ivanov',
        }
        # data
        self.data_template_email = {
            'title': 'Тестовый темплейт',
            'subject': 'Тестовый темплейт {{user.email}}',
            'text': 'Контент текстовый {{user.email}} - {{sometext}}',
            'html': 'Контент HTML {{user.email}} - {{sometext}}',
            'type': TYPE.EMAIL,
            'event': self.PASS_TEST_EVENT,
        }
        self.data_category = {
            'title': 'Основная категория_' + random_char(3),
            'template': '<div>{{text}}</div>',
        }
        self.sometext = 'bla bla'
        self.data_compiled_email = {
            'subject': f'Тестовый темплейт {self.data_user["email"]}',
            'text': f'Контент текстовый {self.data_user["email"]} - {self.sometext}',
            'html': f'Контент HTML {self.data_user["email"]} - {self.sometext}',
            'type': TYPE.EMAIL,
            'event': self.PASS_TEST_EVENT,
        }
        super().setUp()

    def test_notify_email_positive(self):
        # Создание пользователя
        user = User.objects.create_user(**self.data_user)
        # Создание шаблона
        template_email = NotifyTemplate.objects.create(**self.data_template_email)
        template_email = NotifyTemplate.objects.get(pk=template_email.pk)
        self.assertEqual(template_email.title, self.data_template_email['title'])
        self.assertEqual(template_email.subject, self.data_template_email['subject'])
        self.assertEqual(template_email.text, self.data_template_email['text'])
        self.assertEqual(template_email.html, self.data_template_email['html'])
        self.assertEqual(template_email.type, self.data_template_email['type'])
        self.assertEqual(template_email.event, self.data_template_email['event'])
        # Создание категории
        category = NotifyCategory.objects.create(**self.data_category)
        category = NotifyCategory.objects.get(pk=category.pk)
        category.template_choice = template_email
        category.save()
        self.assertEqual(category.title, self.data_category['title'])
        self.assertEqual(category.template, self.data_category['template'])
        self.assertEqual(category.template_choice.id, template_email.id)
        # Создание пробного письма
        Notify.send(self.PASS_TEST_EVENT, {
            'sometext': self.sometext,
            'user': user,
        }, user=user, category=category)
        self.assertEqual(Notify.objects.all().count(), 1)
        notify = Notify.objects.all().first()
        self.assertEqual(notify.subject, self.data_compiled_email['subject'])
        self.assertEqual(notify.text, self.data_compiled_email['text'])
        self.assertEqual(notify.html, self.data_compiled_email['html'])
        self.assertEqual(notify.type, self.data_compiled_email['type'])
        self.assertEqual(notify.event, self.data_compiled_email['event'])
        self.assertEqual(notify.category.id, category.id)

    def test_notify_email_user_list(self):
        # Создание пользователя
        user = User.objects.create_user(**self.data_user)
        # Создание списка
        user_list = NotifyUserList.objects.create(title='userlist_' + random_char(4))
        group = Group.objects.create(name='group_' + random_char(4))
        user_list.user_groups.add(group)

        user_list_participant1 = NotifyUserListParticipant.objects.create(  # noqa
            user_list=user_list,
            email='test2@garpix.com',
        )
        user_list_participant2 = NotifyUserListParticipant.objects.create(  # noqa
            user_list=user_list,
        )
        user_list_participant3 = NotifyUserListParticipant.objects.create(  # noqa
            user_list=user_list,
            email='test3@garpix.com',
        )

        # Создание шаблона
        template_email = NotifyTemplate.objects.create(**self.data_template_email)
        template_email = NotifyTemplate.objects.get(pk=template_email.pk)
        template_email.user_lists.add(user_list)
        template_email.save()

        self.assertEqual(template_email.title, self.data_template_email['title'])
        self.assertEqual(template_email.subject, self.data_template_email['subject'])
        self.assertEqual(template_email.text, self.data_template_email['text'])
        self.assertEqual(template_email.html, self.data_template_email['html'])
        self.assertEqual(template_email.type, self.data_template_email['type'])
        self.assertEqual(template_email.event, self.data_template_email['event'])
        # Создание категории
        category = NotifyCategory.objects.create(**self.data_category)
        category = NotifyCategory.objects.get(pk=category.pk)
        category.template_choice = template_email
        category.save()
        self.assertEqual(category.title, self.data_category['title'])
        self.assertEqual(category.template, self.data_category['template'])
        self.assertEqual(category.template_choice.id, template_email.id)

        # Создание пробного письма
        Notify.send(self.PASS_TEST_EVENT, {
            'sometext': self.sometext,
            'user': user,
        }, user=user, category=category)

        self.assertEqual(Notify.objects.all().count(), 2)

        # notify
        notify = Notify.objects.get(user=user)
        self.assertEqual(notify.subject, self.data_compiled_email['subject'])
        self.assertEqual(notify.text, self.data_compiled_email['text'])
        self.assertEqual(notify.html, self.data_compiled_email['html'])
        self.assertEqual(notify.type, self.data_compiled_email['type'])
        self.assertEqual(notify.event, self.data_compiled_email['event'])
        self.assertEqual(notify.email, 'test@garpix.com')

    def test_notify_viber(self):
        self.data_template_viber = {
            'title': 'Тестовый темплейт',
            'subject': 'Тестовый темплейт {{user.viber_chat_id}}',
            'text': 'Контент текстовый {{user.viber_chat_id}} - {{sometext}}',
            'html': 'Контент HTML {{user.viber_chat_id}} - {{sometext}}',
            'type': TYPE.VIBER,
            'event': self.PASS_TEST_EVENT,
        }
        self.data_viber_user = {
            'username': 'viber_' + random_char(5),
            'viber_secret_key': '111',
            'viber_chat_id': 'm4FsaRu5kBi8HzSAC0liFQ==',
            'password': 'BlaBla123',
            'first_name': 'IvanViber',
            'last_name': 'IvanovViber',
        }
        self.data_compiled_viber = {
            'subject': f'Тестовый темплейт {self.data_viber_user["viber_chat_id"]}',
            'text': f'Контент текстовый {self.data_viber_user["viber_chat_id"]} - {self.sometext}',
            'html': f'Контент HTML {self.data_viber_user["viber_chat_id"]} - {self.sometext}',
            'type': TYPE.VIBER,
            'event': self.PASS_TEST_EVENT,
        }
        # Создание пользователя
        user = User.objects.create_user(**self.data_viber_user)
        # Создание списка
        user_list = NotifyUserList.objects.create(title='viber_' + random_char(4))
        user_list_participant1 = NotifyUserListParticipant.objects.create(  # noqa
            user_list=user_list,
        )
        # Создание шаблона
        template_viber = NotifyTemplate.objects.create(**self.data_template_viber)
        template_viber.user_lists.add(user_list)
        template_viber = NotifyTemplate.objects.get(pk=template_viber.pk)
        self.assertEqual(template_viber.title, self.data_template_viber['title'])
        self.assertEqual(template_viber.subject, self.data_template_viber['subject'])
        self.assertEqual(template_viber.text, self.data_template_viber['text'])
        self.assertEqual(template_viber.html, self.data_template_viber['html'])
        self.assertEqual(template_viber.type, self.data_template_viber['type'])
        self.assertEqual(template_viber.event, self.data_template_viber['event'])
        # Создание категории
        category = NotifyCategory.objects.create(**self.data_category)
        category = NotifyCategory.objects.get(pk=category.pk)
        category.template_choice = template_viber
        category.save()
        self.assertEqual(category.title, self.data_category['title'])
        self.assertEqual(category.template, self.data_category['template'])
        self.assertEqual(category.template_choice.id, template_viber.id)
        Notify.send(self.PASS_TEST_EVENT, {
            'sometext': self.sometext,
            'user': user,
        }, user=user, category=category)
        self.assertEqual(Notify.objects.all().count(), 3)

        # notify 1
        notify = Notify.objects.get(user=user)
        self.assertEqual(notify.subject, self.data_compiled_viber['subject'])
        self.assertEqual(notify.text, self.data_compiled_viber['text'])
        self.assertEqual(notify.html, self.data_compiled_viber['html'])
        self.assertEqual(notify.type, self.data_compiled_viber['type'])
        self.assertEqual(notify.event, self.data_compiled_viber['event'])
        self.assertEqual(notify.user.viber_chat_id, 'm4FsaRu5kBi8HzSAC0liFQ==')
