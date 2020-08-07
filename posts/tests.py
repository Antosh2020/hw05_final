import tempfile
from unittest import mock

from django.core.files import File
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Post, Group, Follow
from django.core.cache import cache


def test_length(self):
    self.assertEqual(len('yatube'), 6)


def test_show_msg(self):
    self.assertTrue(True, msg="Важная проверка на истинность")


class TestNewPostFunc(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sarah", email="connor@yandex.ru", password="sarah")
        self.client_auth = Client()
        self.client.force_login(self.user)
        self.client_unauth = Client()
        self.group = Group.objects.create(title='Змея', slug="anaconda")
        self.post = Post.objects.create(text='crazy', author=self.user,
                                        group=self.group)

        self.user1 = User.objects.create_user(
            username="sam", password="12345")
        self.login1 = self.client.force_login(self.user1)
        self.user2 = User.objects.create_user(
            username="scott", password="12345")
        cache.clear()

    def get_urls(self, post):
        urls = (
            reverse("index"),
            reverse("groups", kwargs={"slug": self.group.slug}),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse("post", kwargs={"username": self.user.username,
                                    "post_id": self.post.id,
                                    }))
        return urls

    def check_post_on_page(self, url, post):
        urls = self.get_urls(post=self.post)
        post_new = Post.objects.all()
        first_post = post_new.first()
        for url in urls:
            self.client_auth.get(url)
            self.assertEqual(first_post.text, self.post.text)
            self.assertEqual(first_post.author, self.post.author)
            self.assertEqual(first_post.group, self.post.group)

    def test_user_page_codes(self):
        response = self.client.get("/sarah/")
        self.assertEqual(response.status_code, 200)

    def test_user_new_post(self):
        """Проверяю, что новый пост от залогиненого пользователя создался
         Сравниваю с двойкой, т.к. 1 пост создается в сетапе, 2 в функции"""
        self.client.force_login(self.user)
        response = self.client.post(reverse("new_post"), follow=True,
                                    data={"text": "crazy",
                                          "group": self.group.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 2)
        post = Post.objects.first()
        urls = self.get_urls(post=self.post)
        for url in urls:
            self.check_post_on_page(url=url, post=post.text)
            self.check_post_on_page(url=url, post=post.author)

    def test_unauthorized_user_new_post(self):
        """Проверяю, что новый пост от незалогиненого пользователя не создался
         Сравниваю с единицей, т.к. 1 пост создается в сетапе"""
        response = self.client_unauth.post(
            reverse('new_post'),
            {
                "text": "пост неавторизованного пользователя"
            }
        )
        self.assertEqual(Post.objects.count(), 1)
        expected_url = reverse('login') + "?next=" + reverse('new_post')
        self.assertRedirects(response, expected_url)

    def test_post_on_page_checker(self):
        urls = self.get_urls(post=self.post)
        for url in urls:
            self.check_post_on_page(url=url, post=self.post.text)
            self.check_post_on_page(url=url, post=self.post.text)

    def test_edit_post(self):
        self.post.text = 'new text'
        self.post.save()
        urls = self.get_urls(post=self.post)
        for url in urls:
            self.check_post_on_page(url=url, post=self.post.text)
            self.check_post_on_page(url=url, post=self.post.text)

    def test_404_not_found(self):
        response = self.client.get("/404/")
        self.assertEqual(response.status_code, 404)

    def test_img_tag_on_post(self):
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('posts/media/pic.jpg', 'rb') as img:
                    self.post.image.save(img.name, img)
                    response = self.client.post(reverse('post', kwargs={
                        'username': self.user.username,
                        'post_id': self.post.id}))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, '<img')

    def test_post_with_img_on_page_check(self):
        urls = self.get_urls(post=self.post)
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open('posts/media/pic.jpg', 'rb') as img:
                    self.post.image.save(img.name, img)
                    for url in urls:
                        response = self.client_auth.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, '<img')

    def test_non_img_upload_fails(self):
        file = mock.MagicMock(spec=File, name="test.txt")
        response = self.client_auth.post(
            reverse('new_post'),
            data={
                'author': self.user,
                'text': 'post text with image',
                'group': self.group.id,
                'image': file
            },
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, form='form', field='image',
                         errors='Неверный формат файла')

    def test_add_post(self):
        self.client.get(reverse('index'))
        post = Post.objects.create(text='crazy', author=self.user)
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, post.text)

    def test_follow_login(self):
        self.client.force_login(self.user1)
        first = Follow.objects.all().count()
        self.client.get(reverse('profile_follow', kwargs={
            'username': 'sarah'}))
        second = Follow.objects.all().count()
        self.assertEqual(first + 1, second)

    def test_unfollow_login(self):
        self.client.force_login(self.user1)
        first = Follow.objects.all().count()
        self.client.get(reverse('profile_unfollow', kwargs={
            'username': 'sarah'}))
        second = Follow.objects.all().count()
        self.assertEqual(first, second)

    def test_follow_index(self):
        self.client.force_login(self.user1)
        self.client.get(reverse('profile_follow', kwargs={
            'username': 'sarah'}))
        response = self.client.get(reverse('follow_index'))
        self.assertContains(response, self.post)

        self.client.force_login(self.user2)
        response = self.client.get(reverse('follow_index'))
        self.assertNotContains(response, self.post)

    def test_auth_user_add_comment(self):
        self.client.force_login(self.user1)
        self.client.get(reverse('post', kwargs={
            'username': self.user, 'post_id': self.post.id}))
        response = self.client.post(reverse('add_comment', kwargs={
            'username': self.user.username, 'post_id': self.post.id}),
                                    {'comment': 'comment'})
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        self.client.get(reverse('post', kwargs={
            'username': self.user, 'post_id': self.post.id}))
        response = self.client.post(reverse('add_comment', kwargs={
            'username': self.user.username, 'post_id': self.post.id}),
                                    {'comment': 'new comment'})
        self.assertEqual(response.status_code, 302)
