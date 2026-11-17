import unittest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.blog import Post, Category, Tag


class Week4TestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        db.create_all()

        # Seed categories
        cat1 = Category(name='Technology', slug='tech', description='Tech articles')
        cat2 = Category(name='Web Development', slug='web-dev', description='Web articles')
        db.session.add_all([cat1, cat2])

        # Seed tags
        tag1 = Tag(name='flask', slug='flask')
        tag2 = Tag(name='python', slug='python')
        db.session.add_all([tag1, tag2])

        # Seed users
        user1 = User(username='sakshi_author', email='sakshi_private@example.com')
        user1.set_password('password123')
        user2 = User(username='bob_user', email='bob_private@example.com')
        user2.set_password('password123')
        db.session.add_all([user1, user2])
        db.session.commit()

        self.user1 = user1
        self.user2 = user2
        self.cat1 = cat1
        self.cat2 = cat2
        self.tag1 = tag1
        self.tag2 = tag2

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, username, password='password123'):
        return self.client.post('/login', data={
            'login_identifier': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def create_sample_posts(self, count=7, author=None, category=None, prefix="sample"):
        if author is None:
            author = self.user1
        if category is None:
            category = self.cat1

        posts = []
        for i in range(1, count + 1):
            p = Post(
                title=f"{prefix.capitalize()} Post Number {i}",
                slug=f"{prefix}-post-number-{i}",
                content=f"<p>This is the full rich text content for post number {i}. It contains valuable information about Flask and web development.</p>",
                category_id=category.id,
                author=author
            )
            p.tags.append(self.tag1)
            db.session.add(p)
            posts.append(p)
        db.session.commit()
        return posts

    # 1. HEALTH CHECK TEST
    def test_health_check(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertEqual(json_data['status'], 'healthy')

    # 2. HOMEPAGE EMPTY STATE TEST
    def test_homepage_empty_state(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('No Blog Posts Published Yet', html)
        self.assertIn('⚡ FlaskStarter', html)
        self.assertIn('Health Check', html)

    # 3. HOMEPAGE WITH POSTS & CARDS TEST
    def test_homepage_with_posts_and_cards(self):
        self.create_sample_posts(count=6)
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        # Home shows latest posts in cards
        self.assertIn('Sample Post Number 6', html)
        self.assertIn('Read More &rarr;', html)
        self.assertIn('sakshi_author', html)
        self.assertIn('Technology', html)
        self.assertIn('#flask', html)
        # Excerpt is present
        self.assertIn('This is the full rich text content', html)
        # Pagination should appear because count (6) > per_page (5)
        self.assertIn('pagination-wrapper', html)
        self.assertIn('Page 1 of 2', html)

    # 4. PAGINATION ACROSS MULTIPLE PAGES TEST
    def test_pagination_pages(self):
        self.create_sample_posts(count=7)

        # Page 1
        res1 = self.client.get('/blog/?page=1')
        self.assertEqual(res1.status_code, 200)
        html1 = res1.data.decode('utf-8')
        self.assertIn('Sample Post Number 7', html1)
        self.assertIn('Sample Post Number 3', html1)
        self.assertNotIn('Sample Post Number 2', html1)  # On page 2
        self.assertIn('Next &rarr;', html1)

        # Page 2
        res2 = self.client.get('/blog/?page=2')
        self.assertEqual(res2.status_code, 200)
        html2 = res2.data.decode('utf-8')
        self.assertIn('Sample Post Number 2', html2)
        self.assertIn('Sample Post Number 1', html2)
        self.assertNotIn('Sample Post Number 7', html2)
        self.assertIn('&larr; Previous', html2)

        # Handle invalid page safely (out of range or negative)
        res_invalid = self.client.get('/blog/?page=999')
        self.assertEqual(res_invalid.status_code, 200)
        res_negative = self.client.get('/blog/?page=-5')
        self.assertEqual(res_negative.status_code, 200)

    # 5. PAGINATION PRESERVES FILTERS TEST
    def test_pagination_preserves_filters(self):
        # Create 6 posts in Tech and 6 in Web-Dev
        self.create_sample_posts(count=6, category=self.cat1, prefix="tech")
        self.create_sample_posts(count=6, category=self.cat2, prefix="web")

        # Filter by category tech
        res = self.client.get('/blog/?category=tech&page=1')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('category=tech', html)
        self.assertIn('page=2', html)

        # Filter by search query
        res_search = self.client.get('/blog/?q=Number&page=1')
        self.assertEqual(res_search.status_code, 200)
        html_search = res_search.data.decode('utf-8')
        self.assertIn('q=Number', html_search)

    # 6. INDIVIDUAL BLOG POST PAGE TEST
    def test_individual_post_page(self):
        self.create_sample_posts(count=1)
        post = Post.query.first()

        res = self.client.get(f'/blog/{post.slug}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn(post.title, html)
        self.assertIn(post.author.username, html)
        self.assertIn('Technology', html)
        self.assertIn('Back to All Posts', html)
        self.assertIn('About the Author', html)
        # Edit/Delete controls should NOT be visible to unauthenticated guests
        self.assertNotIn('✏️ Edit Post', html)

    # 7. AUTHORIZATION RESTRICTIONS (EDIT & DELETE) TEST
    def test_post_edit_delete_authorization(self):
        self.create_sample_posts(count=1, author=self.user1)
        post = Post.query.first()

        # Guest cannot edit
        res_guest_edit = self.client.get(f'/blog/{post.slug}/edit')
        self.assertEqual(res_guest_edit.status_code, 302)  # Redirect to login

        # Bob (not author) logs in and attempts to edit post
        self.login('bob_user')
        res_bob_edit = self.client.get(f'/blog/{post.slug}/edit')
        self.assertEqual(res_bob_edit.status_code, 403)
        self.assertIn('403 Forbidden', res_bob_edit.data.decode('utf-8'))

        # Bob attempts to delete post
        res_bob_del = self.client.post(f'/blog/{post.slug}/delete')
        self.assertEqual(res_bob_del.status_code, 403)
        self.logout()

        # Author (sakshi_author) logs in and can view edit form
        self.login('sakshi_author')
        res_author_view = self.client.get(f'/blog/{post.slug}')
        self.assertIn('✏️ Edit Post', res_author_view.data.decode('utf-8'))

        res_author_edit = self.client.get(f'/blog/{post.slug}/edit')
        self.assertEqual(res_author_edit.status_code, 200)

        # Author can delete post
        res_author_del = self.client.post(f'/blog/{post.slug}/delete', follow_redirects=True)
        self.assertEqual(res_author_del.status_code, 200)
        self.assertIsNone(Post.query.filter_by(id=post.id).first())
        self.logout()

    # 8. USER PROFILE PAGE TEST & SENSITIVE DATA PROTECTION
    def test_user_profile_page(self):
        self.create_sample_posts(count=3, author=self.user1)

        # Public profile for user1
        res = self.client.get('/user/sakshi_author')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('sakshi_author', html)
        self.assertIn('Articles Authored by @sakshi_author', html)
        self.assertIn('Sample Post Number 1', html)
        self.assertIn('Sample Post Number 2', html)
        self.assertIn('Sample Post Number 3', html)

        # STRICT PRIVACY & SECURITY CHECK:
        # Email address must NEVER appear on public profile
        self.assertNotIn('sakshi_private@example.com', html)
        # Password hash must NEVER appear
        self.assertNotIn('password_hash', html)
        self.assertNotIn('pbkdf2', html)
        self.assertNotIn('scrypt', html)

    # 9. USER PROFILE EMPTY STATE TEST
    def test_user_profile_empty_state(self):
        # User2 has 0 posts
        res = self.client.get('/user/bob_user')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('No articles published yet', html)
        self.assertIn('bob_user', html)
        self.assertNotIn('bob_private@example.com', html)

    # 10. NONEXISTENT USER PROFILE GRACEFUL 404 TEST
    def test_nonexistent_user_profile_404(self):
        res = self.client.get('/user/nonexistent_ghost_user')
        self.assertEqual(res.status_code, 404)
        html = res.data.decode('utf-8')
        self.assertIn('User Not Found', html)
        self.assertIn('404 Error', html)

    # 11. NAVIGATION BAR STATE TEST (GUEST VS AUTHENTICATED)
    def test_navigation_bar_states(self):
        # Guest navbar
        res_guest = self.client.get('/')
        html_guest = res_guest.data.decode('utf-8')
        self.assertIn('Home', html_guest)
        self.assertIn('Blog', html_guest)
        self.assertIn('Health Check', html_guest)
        self.assertIn('Login', html_guest)
        self.assertIn('Register', html_guest)
        self.assertNotIn('Dashboard', html_guest)
        self.assertNotIn('Write Post', html_guest)

        # Authenticated navbar
        self.login('sakshi_author')
        res_auth = self.client.get('/')
        html_auth = res_auth.data.decode('utf-8')
        self.assertIn('Home', html_auth)
        self.assertIn('Blog', html_auth)
        self.assertIn('Health Check', html_auth)
        self.assertIn('✍️ Write Post', html_auth)
        self.assertIn('Dashboard', html_auth)
        self.assertIn('👤 sakshi_author', html_auth)
        self.assertIn('Logout', html_auth)
        self.assertNotIn('Register</a>', html_auth)
        self.logout()

    # 12. SHORTCUT ROUTE /profile REDIRECT TEST
    def test_profile_shortcut_route(self):
        # When logged out -> redirect to login
        res_guest = self.client.get('/profile', follow_redirects=False)
        self.assertEqual(res_guest.status_code, 302)
        self.assertIn('/login', res_guest.headers['Location'])

        # When logged in -> redirect to /user/<username>
        self.login('sakshi_author')
        res_auth = self.client.get('/profile', follow_redirects=False)
        self.assertEqual(res_auth.status_code, 302)
        self.assertIn('/user/sakshi_author', res_auth.headers['Location'])
        self.logout()

    # 13. USER REGISTRATION AND LOGIN FLOW TEST (TASK 2 PRESERVATION)
    def test_registration_and_login_flow(self):
        # Register new user
        res_reg = self.client.post('/register', data={
            'username': 'newbie_dev',
            'email': 'newbie@example.com',
            'password': 'secretpassword',
            'confirm_password': 'secretpassword'
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn('Registration successful', res_reg.data.decode('utf-8'))

        # Log in with new user
        res_login = self.login('newbie_dev', 'secretpassword')
        self.assertEqual(res_login.status_code, 200)
        self.assertIn('Welcome back, newbie_dev!', res_login.data.decode('utf-8'))

        # Dashboard accessible
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn('newbie_dev', res_dash.data.decode('utf-8'))
        self.assertIn('/user/newbie_dev', res_dash.data.decode('utf-8'))

        # Logout
        res_logout = self.logout()
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn('logged out successfully', res_logout.data.decode('utf-8'))

    # 14. BLOG CRUD VIA FORMS TEST (TASK 3 PRESERVATION)
    def test_blog_crud_form_flow(self):
        self.login('sakshi_author')

        # Create Post via POST
        res_create = self.client.post('/blog/create', data={
            'title': 'CRUD Life Cycle in Flask',
            'slug': 'crud-lifecycle-flask',
            'category_id': self.cat1.id,
            'tags': 'flask, python, architecture',
            'content': '<p>This is a complete guide to Flask CRUD operations.</p>'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        html_create = res_create.data.decode('utf-8')
        self.assertIn('Your blog post has been published successfully!', html_create)
        self.assertIn('CRUD Life Cycle in Flask', html_create)

        # Edit Post via POST
        res_edit = self.client.post('/blog/crud-lifecycle-flask/edit', data={
            'title': 'CRUD Life Cycle in Flask - Updated Edition',
            'slug': 'crud-lifecycle-flask',
            'category_id': self.cat1.id,
            'tags': 'flask, python, architecture, updated',
            'content': '<p>Updated content with advanced techniques.</p>'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        html_edit = res_edit.data.decode('utf-8')
        self.assertIn('Your blog post has been updated successfully!', html_edit)
        self.assertIn('CRUD Life Cycle in Flask - Updated Edition', html_edit)

        # Delete Post via POST
        res_delete = self.client.post('/blog/crud-lifecycle-flask/delete', follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)
        html_delete = res_delete.data.decode('utf-8')
        self.assertIn('The blog post has been deleted successfully.', html_delete)
        self.logout()

    # 15. USER PROFILE PAGINATION TEST
    def test_user_profile_pagination(self):
        # Create 8 posts for user1
        self.create_sample_posts(count=8, author=self.user1, prefix="authorposts")

        # Page 1 of profile
        res1 = self.client.get('/user/sakshi_author?page=1')
        self.assertEqual(res1.status_code, 200)
        html1 = res1.data.decode('utf-8')
        self.assertIn('Authorposts Post Number 8', html1)
        self.assertIn('Authorposts Post Number 4', html1)
        self.assertIn('pagination-wrapper', html1)
        self.assertIn('Page 1 of 2', html1)

        # Page 2 of profile
        res2 = self.client.get('/user/sakshi_author?page=2')
        self.assertEqual(res2.status_code, 200)
        html2 = res2.data.decode('utf-8')
        self.assertIn('Authorposts Post Number 3', html2)
        self.assertIn('Authorposts Post Number 1', html2)
        self.assertNotIn('Authorposts Post Number 8', html2)

    # 16. ROBUST PAGINATION PARAMETER HANDLING
    def test_pagination_non_numeric_params(self):
        self.create_sample_posts(count=6)
        # Passing letters for page
        res = self.client.get('/blog/?page=abc')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Sample Post Number 6', html)

        # Passing 0 for page
        res0 = self.client.get('/blog/?page=0')
        self.assertEqual(res0.status_code, 200)


if __name__ == '__main__':
    unittest.main()
