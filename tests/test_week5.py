"""
Week 5 Test Suite: Commenting System

Tests cover:
- Comment model creation and DB relationships
- Authenticated comment submission
- Comment appears on the correct post
- Correct author username and timestamp displayed
- Unauthenticated users cannot submit comments
- Empty / whitespace-only comments are rejected
- Author can delete their own comment
- Non-author cannot delete someone else's comment
- Comments remain associated with the correct post
- Existing blog CRUD functionality preserved
- Existing auth and dashboard preserved
- Existing pagination, navigation, profile pages preserved
"""

import unittest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.blog import Post, Category, Tag, Comment


class Week5CommentTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

        db.create_all()

        # Seed categories
        cat1 = Category(name='Technology', slug='tech', description='Tech articles')
        cat2 = Category(name='General', slug='general', description='General articles')
        db.session.add_all([cat1, cat2])

        # Seed tags
        tag1 = Tag(name='flask', slug='flask')
        db.session.add(tag1)

        # Seed users
        user1 = User(username='alice_dev', email='alice_private@example.com')
        user1.set_password('password123')
        user2 = User(username='bob_reader', email='bob_private@example.com')
        user2.set_password('password123')
        db.session.add_all([user1, user2])
        db.session.commit()

        self.user1 = user1
        self.user2 = user2
        self.cat1 = cat1
        self.tag1 = tag1

        # Seed a sample post authored by user1
        post = Post(
            title='My Test Flask Post',
            slug='my-test-flask-post',
            content='<p>This is sample content about Flask development.</p>',
            category_id=cat1.id,
            author=user1
        )
        post.tags.append(tag1)
        db.session.add(post)
        db.session.commit()

        self.post = post

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

    def post_comment(self, slug, body, follow=True):
        """Helper: POST a comment as the currently logged-in user."""
        return self.client.post(
            f'/blog/{slug}/comment',
            data={'body': body, 'csrf_token': 'test_token'},
            follow_redirects=follow
        )

    # -----------------------------------------------------------------------
    # 1. COMMENT MODEL – DATABASE CREATION & RELATIONSHIPS
    # -----------------------------------------------------------------------

    def test_comment_model_creation(self):
        """Comment can be created and saved to the DB with correct FK links."""
        comment = Comment(
            body='Great post! Really helpful.',
            post_id=self.post.id,
            user_id=self.user1.id
        )
        db.session.add(comment)
        db.session.commit()

        fetched = Comment.query.get(comment.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.body, 'Great post! Really helpful.')
        self.assertEqual(fetched.post_id, self.post.id)
        self.assertEqual(fetched.user_id, self.user1.id)
        self.assertIsNotNone(fetched.created_at)

    def test_comment_post_relationship(self):
        """Comment.post returns the correct Post instance."""
        comment = Comment(body='Nice work!', post_id=self.post.id, user_id=self.user2.id)
        db.session.add(comment)
        db.session.commit()

        self.assertEqual(comment.post.id, self.post.id)
        self.assertEqual(comment.post.title, 'My Test Flask Post')

    def test_comment_author_relationship(self):
        """Comment.author returns the correct User instance."""
        comment = Comment(body='Love this!', post_id=self.post.id, user_id=self.user2.id)
        db.session.add(comment)
        db.session.commit()

        self.assertEqual(comment.author.username, 'bob_reader')

    def test_post_comments_relationship(self):
        """Post.comments returns all associated comments."""
        c1 = Comment(body='First comment.', post_id=self.post.id, user_id=self.user1.id)
        c2 = Comment(body='Second comment.', post_id=self.post.id, user_id=self.user2.id)
        db.session.add_all([c1, c2])
        db.session.commit()

        count = self.post.comments.count()
        self.assertEqual(count, 2)

    def test_delete_post_cascades_comments(self):
        """Deleting a post also deletes all its comments (cascade)."""
        c1 = Comment(body='Will be deleted.', post_id=self.post.id, user_id=self.user1.id)
        db.session.add(c1)
        db.session.commit()
        comment_id = c1.id

        db.session.delete(self.post)
        db.session.commit()

        # Comment should be gone
        self.assertIsNone(Comment.query.get(comment_id))

    def test_user_comments_relationship(self):
        """User.comments returns all comments authored by that user."""
        c1 = Comment(body='My comment.', post_id=self.post.id, user_id=self.user1.id)
        db.session.add(c1)
        db.session.commit()

        count = self.user1.comments.count()
        self.assertEqual(count, 1)

    # -----------------------------------------------------------------------
    # 2. AUTHENTICATED USER CAN SUBMIT A COMMENT
    # -----------------------------------------------------------------------

    def test_authenticated_user_can_submit_comment(self):
        """Logged-in user submitting a valid comment gets success flash."""
        self.login('alice_dev')
        res = self.post_comment(self.post.slug, 'This is an insightful article!')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Your comment has been posted successfully!', html)

    def test_comment_stored_in_database(self):
        """Submitted comment is persisted in the DB with correct data."""
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Stored DB comment text.')

        comment = Comment.query.filter_by(post_id=self.post.id).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.body, 'Stored DB comment text.')
        self.assertEqual(comment.user_id, self.user1.id)
        self.assertEqual(comment.post_id, self.post.id)

    # -----------------------------------------------------------------------
    # 3. COMMENT APPEARS ON CORRECT BLOG POST
    # -----------------------------------------------------------------------

    def test_comment_displayed_on_correct_post(self):
        """Comment text appears when viewing the specific post's detail page."""
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Visible on this post only.')
        self.logout()

        res = self.client.get(f'/blog/{self.post.slug}')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Visible on this post only.', html)

    def test_comment_shows_author_username(self):
        """Comment shows the author's username correctly."""
        self.login('bob_reader')
        self.post_comment(self.post.slug, 'Comment from bob reader.')
        self.logout()

        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        self.assertIn('bob_reader', html)

    def test_comment_shows_timestamp(self):
        """Comment displays a formatted date/time string."""
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Comment with timestamp.')
        self.logout()

        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        # Should contain the year (at minimum)
        self.assertIn('2026', html)

    def test_comment_not_on_other_post(self):
        """Comment submitted to one post does not appear on another post."""
        # Create a second post
        post2 = Post(
            title='Another Post',
            slug='another-post',
            content='<p>Different content.</p>',
            category_id=self.cat1.id,
            author=self.user1
        )
        db.session.add(post2)
        db.session.commit()

        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Only on first post.')
        self.logout()

        res = self.client.get(f'/blog/{post2.slug}')
        html = res.data.decode('utf-8')
        self.assertNotIn('Only on first post.', html)

    # -----------------------------------------------------------------------
    # 4. UNAUTHENTICATED USER CANNOT SUBMIT
    # -----------------------------------------------------------------------

    def test_unauthenticated_cannot_submit_comment(self):
        """Guest is redirected to login when attempting to POST a comment."""
        res = self.client.post(
            f'/blog/{self.post.slug}/comment',
            data={'body': 'Anonymous comment attempt'},
            follow_redirects=False
        )
        # Should redirect (302) since login_required kicks in
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_unauthenticated_sees_login_prompt(self):
        """Guest viewing a post sees a login/register prompt instead of the form."""
        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        self.assertIn('Log in', html)
        self.assertIn('register', html)
        self.assertNotIn('Post Comment', html)

    # -----------------------------------------------------------------------
    # 5. EMPTY / INVALID COMMENT REJECTION
    # -----------------------------------------------------------------------

    def test_empty_comment_rejected(self):
        """An empty body comment is rejected with a validation error message."""
        self.login('alice_dev')
        res = self.post_comment(self.post.slug, '')
        html = res.data.decode('utf-8')
        # Should show an error flash or stay on post without success message
        self.assertNotIn('Your comment has been posted successfully!', html)
        # Empty comment must not be stored
        count = Comment.query.filter_by(post_id=self.post.id).count()
        self.assertEqual(count, 0)

    def test_whitespace_only_comment_rejected(self):
        """A comment with only whitespace is rejected."""
        self.login('alice_dev')
        res = self.post_comment(self.post.slug, '   \n\t   ')
        html = res.data.decode('utf-8')
        self.assertNotIn('Your comment has been posted successfully!', html)
        count = Comment.query.filter_by(post_id=self.post.id).count()
        self.assertEqual(count, 0)

    def test_too_long_comment_rejected(self):
        """A comment exceeding 1000 characters is rejected."""
        self.login('alice_dev')
        long_body = 'A' * 1001
        res = self.post_comment(self.post.slug, long_body)
        html = res.data.decode('utf-8')
        self.assertNotIn('Your comment has been posted successfully!', html)
        count = Comment.query.filter_by(post_id=self.post.id).count()
        self.assertEqual(count, 0)

    # -----------------------------------------------------------------------
    # 6. COMMENT DELETION
    # -----------------------------------------------------------------------

    def test_author_can_delete_own_comment(self):
        """Comment author can delete their own comment successfully."""
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Comment to delete.')

        comment = Comment.query.filter_by(post_id=self.post.id).first()
        self.assertIsNotNone(comment)

        res = self.client.post(
            f'/blog/{self.post.slug}/comment/{comment.id}/delete',
            data={'csrf_token': 'test_token'},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Comment deleted successfully.', html)

        # Comment should no longer exist in DB
        deleted = Comment.query.get(comment.id)
        self.assertIsNone(deleted)

    def test_non_author_cannot_delete_comment(self):
        """A user cannot delete a comment they did not write (403)."""
        # alice posts a comment
        self.login('alice_dev')
        self.post_comment(self.post.slug, "Alice's comment.")
        self.logout()

        comment = Comment.query.filter_by(post_id=self.post.id).first()
        self.assertIsNotNone(comment)

        # bob tries to delete alice's comment
        self.login('bob_reader')
        res = self.client.post(
            f'/blog/{self.post.slug}/comment/{comment.id}/delete',
            data={'csrf_token': 'test_token'},
            follow_redirects=False
        )
        self.assertEqual(res.status_code, 403)

        # Comment should still exist
        still_exists = Comment.query.get(comment.id)
        self.assertIsNotNone(still_exists)

    def test_unauthenticated_cannot_delete_comment(self):
        """Unauthenticated user is redirected when trying to delete a comment."""
        comment = Comment(body='Protected comment.', post_id=self.post.id, user_id=self.user1.id)
        db.session.add(comment)
        db.session.commit()

        res = self.client.post(
            f'/blog/{self.post.slug}/comment/{comment.id}/delete',
            follow_redirects=False
        )
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_delete_button_shown_only_to_comment_owner(self):
        """The delete button is visible only to the comment's author, not others."""
        # alice posts a comment
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'Alice wrote this comment.')
        self.logout()

        comment = Comment.query.filter_by(post_id=self.post.id).first()

        # alice sees her delete button
        self.login('alice_dev')
        res_alice = self.client.get(f'/blog/{self.post.slug}')
        html_alice = res_alice.data.decode('utf-8')
        self.assertIn(f'/comment/{comment.id}/delete', html_alice)
        self.logout()

        # bob does NOT see the delete button for alice's comment
        self.login('bob_reader')
        res_bob = self.client.get(f'/blog/{self.post.slug}')
        html_bob = res_bob.data.decode('utf-8')
        self.assertNotIn(f'/comment/{comment.id}/delete', html_bob)
        self.logout()

    # -----------------------------------------------------------------------
    # 7. COMMENT COUNT DISPLAY
    # -----------------------------------------------------------------------

    def test_comment_count_zero_state(self):
        """Post with no comments shows 0 in the count badge and empty-state message."""
        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        self.assertIn('comments-count-badge', html)
        self.assertIn('No comments yet', html)

    def test_comment_count_increments(self):
        """Comment count badge increments after a comment is added."""
        self.login('alice_dev')
        self.post_comment(self.post.slug, 'First comment ever.')
        self.post_comment(self.post.slug, 'Second comment.')
        self.logout()

        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        # The badge should contain '2'
        self.assertIn('>2<', html)

    # -----------------------------------------------------------------------
    # 8. COMMENTS SECTION STRUCTURE ON PAGE
    # -----------------------------------------------------------------------

    def test_comments_section_present_on_post_page(self):
        """The comments section is rendered on a post's detail page."""
        res = self.client.get(f'/blog/{self.post.slug}')
        html = res.data.decode('utf-8')
        self.assertIn('comments-section', html)
        self.assertIn('💬 Comments', html)

    # -----------------------------------------------------------------------
    # 9. BACKWARD-COMPATIBILITY: EXISTING FUNCTIONALITY PRESERVED
    # -----------------------------------------------------------------------

    def test_existing_blog_index_still_works(self):
        """Blog index page loads fine after adding commenting system."""
        res = self.client.get('/blog/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('FlaskStarter', html)

    def test_existing_post_crud_preserved(self):
        """Create, edit, and delete blog posts continue to work."""
        self.login('alice_dev')

        # Create
        res_create = self.client.post('/blog/create', data={
            'title': 'Week 5 Preservation Test Post',
            'slug': 'week5-preservation-test',
            'category_id': self.cat1.id,
            'tags': 'flask',
            'content': '<p>This post tests backward compatibility.</p>'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn('published successfully', res_create.data.decode('utf-8'))

        # Edit
        res_edit = self.client.post('/blog/week5-preservation-test/edit', data={
            'title': 'Week 5 Preservation Test Post Updated',
            'slug': 'week5-preservation-test',
            'category_id': self.cat1.id,
            'tags': 'flask, python',
            'content': '<p>Updated content for preservation check.</p>'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn('updated successfully', res_edit.data.decode('utf-8'))

        # Delete
        res_delete = self.client.post('/blog/week5-preservation-test/delete', follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)
        self.assertIn('deleted successfully', res_delete.data.decode('utf-8'))

        self.logout()

    def test_existing_auth_dashboard_preserved(self):
        """Login, dashboard and logout continue to function."""
        res = self.login('alice_dev')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Welcome back, alice_dev!', res.data.decode('utf-8'))

        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn('alice_dev', res_dash.data.decode('utf-8'))

        res_logout = self.logout()
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn('logged out successfully', res_logout.data.decode('utf-8'))

    def test_existing_user_profile_preserved(self):
        """User profile page still loads correctly."""
        res = self.client.get('/user/alice_dev')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('alice_dev', html)
        # Privacy: email must not be exposed
        self.assertNotIn('alice_private@example.com', html)

    def test_existing_navigation_preserved(self):
        """Navigation bar renders correctly for guests and authenticated users."""
        # Guest navbar
        res = self.client.get('/')
        html = res.data.decode('utf-8')
        self.assertIn('Login', html)
        self.assertIn('Register', html)

        # Auth navbar
        self.login('alice_dev')
        res_auth = self.client.get('/')
        html_auth = res_auth.data.decode('utf-8')
        self.assertIn('Dashboard', html_auth)
        self.assertIn('Logout', html_auth)
        self.logout()


if __name__ == '__main__':
    unittest.main()
