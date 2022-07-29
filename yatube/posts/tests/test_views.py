from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Group, Post, Comment
from django.core.cache import cache
from http import HTTPStatus

User = get_user_model()


class PostTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_name')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста',
            id=1,
            group=Group.objects.create(
                title='Заголовок для тестовой группы',
                slug='test_slug'))

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:profile', kwargs={'username': 'test_name'})):
            'posts/profile.html',
            (reverse('posts:post_detail', kwargs={'post_id': 1})):
            'posts/post_detail.html',
            (reverse('posts:post_edit', kwargs={'post_id': 1})):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            (reverse('posts:group_posts', kwargs={'slug': 'test_slug'})):
            'posts/group_list.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context["page_obj"][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author.username
        post_group_0 = first_object.group.title
        self.assertEqual(post_text_0, 'Текст поста')
        self.assertEqual(post_author_0, 'test_name')
        self.assertEqual(post_group_0, 'Заголовок для тестовой группы')

    def test_group_pages_show_correct_context(self):
        """Шаблон group_posts сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse
                                              ('posts:group_posts',
                                               kwargs={'slug': 'test_slug'}))
        first_object = response.context["group"]
        group_title_0 = first_object.title
        group_slug_0 = first_object.slug
        self.assertEqual(group_title_0, 'Заголовок для тестовой группы')
        self.assertEqual(group_slug_0, 'test_slug')

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (
            self.authorized_client.get(reverse(
                'posts:post_detail', kwargs={'post_id': 1}))
        )
        self.assertEqual(
            response.context.get('post').author.username, 'test_name'
        )
        self.assertEqual(response.context.get('post').text, 'Текст поста')
        self.assertEqual(response.context.get('post').id, 1)

    def test_new_post_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'test_name'}))
        first_object = response.context["page_obj"][0]
        post_text_0 = first_object.text
        self.assertEqual(response.context['author'].username, 'test_name')
        self.assertEqual(post_text_0, 'Текст поста')

    def test_post_another_group(self):
        """Пост не попал в другую группу."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': 'test_slug'}))
        first_object = response.context["page_obj"][0]
        post_text_0 = first_object.text
        self.assertTrue(post_text_0, 'Тестовая запись для создания поста')

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_name',
                                              email='test@mail.ru',
                                              password='test_pass',)
        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug1',
            description='Тестовое описание')
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group))
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='mob2556')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_second_page_contains_three_posts(self):
        """Паджинация по три поста на странице."""
        list_urls = {
            reverse('posts:index') + '?page=2': 'index',
            reverse('posts:group_posts', kwargs={'slug':
                    'test_slug1'}) + '?page=2': 'group',
            reverse('posts:profile', kwargs={'username':
                    'test_name'}) + '?page=2': 'profile',
        }
        for tested_url in list_urls.keys():
            response = self.client.get(tested_url)
            self.assertEqual(
                len(response.context.get('page_obj').object_list), 3
            )


class CommentViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()

        cls.auth_user = User.objects.create_user(
            username='test_auth_user'
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.auth_user)

        cls.author = User.objects.create_user(
            username='test_author'
        )
        cls.auth_author_client = Client()
        cls.auth_author_client.force_login(cls.author)

        cls.group = Group.objects.create(
            title='test_group',
            slug='test-slug',
            description='test_description'
        )

        cls.post = Post.objects.create(
            text='test_post',
            group=cls.group,
            author=cls.author
        )

    def test_add_comment_for_guest(self):
        response = CommentViewsTest.guest_client.get(
            reverse(
                'posts:add_comment',
                kwargs={
                    'post_id': CommentViewsTest.post.pk
                }
            )
        )
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            ('Неавторизированный пользователь'
             ' не может оставлять комментарий')
        )

    def test_comment_for_auth_user(self):
        """Авторизированный пользователь может оставить комментарий"""
        client = CommentViewsTest.authorized_client
        post = CommentViewsTest.post
        response = self.client.post(
            reverse('posts:add_comment',
                    kwargs={
                        'post_id': post.pk
                    }),
            follow=True
        )
        self.assertEqual(
            response.status_code,
            HTTPStatus.OK,
            ('Авторизированный пользователь'
             ' должен иметь возможность'
             ' оставлять комментарий')
        )
        comments_count = Comment.objects.filter(
            post=post.pk
        ).count()
        form_data = {
            'text': 'test_comment',
        }

        response = client.post(
            reverse('posts:add_comment',
                    kwargs={
                        'post_id': post.pk
                    }
                    ),
            data=form_data,
            follow=True
        )
        comments = Post.objects.filter(
            id=post.pk
        ).values_list('comments', flat=True)
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': post.pk
                }
            )
        )
        self.assertEqual(
            comments.count(),
            comments_count + 1
        )
        self.assertTrue(
            Comment.objects.filter(
                post=post.pk,
                author=CommentViewsTest.auth_user.pk,
                text=form_data['text']
            ).exists()
        )
