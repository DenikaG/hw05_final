from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_name')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись для создания нового поста',
            id=1)

        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug'
        )

    def test_home_and_group(self):
        """страницы группы и главная доступны всем."""
        url_names = (
            '/',
            '/group/test_slug/',
        )
        for adress in url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_new_for_authorized(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_url(self):
        """без авторизации приватные URL недоступны."""
        url_names = (
            '/create/',
            '/admin/',
            '/posts/1/edit/'
        )
        for adress in url_names:
            with self.subTest():
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_redirect_anonymous_on_login(self):
        """Страница '/create/' и '/posts/1/edit/' перенаправит анонимного пользователя
        на страницу логина.
        """
        response_create = self.guest_client.get('/create/', follow=True)
        response_edit = self.guest_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(response_create, '/auth/login/?next=/create/')
        self.assertRedirects(response_edit, '/auth/login/?next=/posts/1/edit/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/profile/test_name/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/qwerty12345/': 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_page_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('/qwerty12345/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
