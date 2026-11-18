
import unittest

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.blog import Post, Category, Tag


class SearchFilteringTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        db.create_all()

        self.user = User(
            username='test_author',
            email='test_author@example.com'
        )
        self.user.set_password('password123')

        self.category = Category(
            name='Python & Flask',
            slug='python-flask',
            description='Python articles'
        )

        self.other_category = Category(
            name='Web Development',
            slug='web-dev',
            description='Web articles'
        )

        self.tag = Tag(name='python', slug='python')
        self.other_tag = Tag(name='flask', slug='flask')

        db.session.add_all([
            self.user,
            self.category,
            self.other_category,
            self.tag,
            self.other_tag
        ])
        db.session.commit()

        self.create_posts()

    def create_posts(self):
        for i in range(1, 8):
            post = Post(
                title=f'Python Tutorial {i}',
                slug=f'python-tutorial-{i}',
                content=(
                    f'This article explains lightweight '
                    f'Python programming example {i}.'
                ),
                category_id=self.category.id,
                author=self.user
            )

            post.tags.append(self.tag)
            db.session.add(post)

        other_post = Post(
            title='Flask Web Development',
            slug='flask-web-development',
            content='Building applications with Flask.',
            category_id=self.other_category.id,
            author=self.user
        )

        other_post.tags.append(self.other_tag)
        db.session.add(other_post)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_search_by_title(self):
        response = self.client.get(
            '/blog/?q=Python Tutorial'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Python Tutorial',
            response.data
        )

    def test_search_by_content(self):
        response = self.client.get(
            '/blog/?q=lightweight'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Python Tutorial',
            response.data
        )

    def test_category_filter(self):
        response = self.client.get(
            '/blog/?category=python-flask'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Python Tutorial',
            response.data
        )
        self.assertNotIn(
            b'Flask Web Development',
            response.data
        )

    def test_tag_filter(self):
        response = self.client.get(
            '/blog/?tag=python'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Python Tutorial',
            response.data
        )
        self.assertNotIn(
            b'Flask Web Development',
            response.data
        )

    def test_combined_search_and_category(self):
        response = self.client.get(
            '/blog/?q=Python&category=python-flask'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Python Tutorial',
            response.data
        )

    def test_search_no_results(self):
        response = self.client.get(
            '/blog/?q=nonexistentkeyword'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'No blog posts found',
            response.data
        )

    def test_pagination(self):
        response = self.client.get('/blog/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'pagination-wrapper',
            response.data
        )

        response_page_two = self.client.get('/blog/?page=2')
        self.assertEqual(response_page_two.status_code, 200)


if __name__ == '__main__':
    unittest.main()
