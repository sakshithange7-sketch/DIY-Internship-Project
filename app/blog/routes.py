from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blog import blog_bp
from app.blog.forms import PostForm, CategoryForm
from app.models.blog import Post, Category, Tag


def ensure_default_categories():
    """
    Ensure a baseline set of categories exists so users can immediately
    categorize blog posts upon first launch.
    """
    if Category.query.first() is None:
        defaults = [
            ('Technology', 'tech', 'Articles covering software engineering and technology.'),
            ('Web Development', 'web-dev', 'Modern full-stack web development with Python and Flask.'),
            ('Python & Flask', 'python-flask', 'Deep dives into Flask, Jinja, SQLAlchemy, and Python patterns.'),
            ('General', 'general', 'General thoughts, insights, and community updates.')
        ]
        for name, slug, desc in defaults:
            cat = Category(name=name, slug=slug, description=desc)
            db.session.add(cat)
        db.session.commit()


def process_tags(tags_input):
    """
    Parses a comma-separated string of tag names, retrieves existing tags
    or creates new ones, and returns a list of Tag objects.
    """
    if not tags_input:
        return []

    tags = []
    seen = set()
    for raw_tag in tags_input.split(','):
        tag_name = raw_tag.strip()
        if not tag_name:
            continue
        tag_slug = Tag.slugify(tag_name)
        if tag_slug in seen:
            continue
        seen.add(tag_slug)

        tag = Tag.query.filter_by(slug=tag_slug).first()
        if not tag:
            tag = Tag(name=tag_name, slug=tag_slug)
            db.session.add(tag)
        tags.append(tag)
    return tags


@blog_bp.route('/')
def index():
    """
    Blog index listing all blog posts.
    Supports filtering by category (?category=slug), tag (?tag=slug), and search query (?q=text).
    """
    ensure_default_categories()

    query = Post.query
    selected_category = None
    selected_tag = None
    search_query = request.args.get('q', '').strip()
    category_slug = request.args.get('category', '').strip()
    tag_slug = request.args.get('tag', '').strip()

    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug).first()
        if selected_category:
            query = query.filter_by(category_id=selected_category.id)

    if tag_slug:
        selected_tag = Tag.query.filter_by(slug=tag_slug).first()
        if selected_tag:
            query = query.filter(Post.tags.contains(selected_tag))

    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            (Post.title.ilike(search_filter)) | (Post.content.ilike(search_filter))
        )

    posts = query.order_by(Post.created_at.desc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        'blog/index.html',
        posts=posts,
        categories=categories,
        selected_category=selected_category,
        selected_tag=selected_tag,
        search_query=search_query
    )


@blog_bp.route('/category/<slug>')
def category_view(slug):
    """Convenience route to filter posts by category slug."""
    return redirect(url_for('blog.index', category=slug))


@blog_bp.route('/tag/<slug>')
def tag_view(slug):
    """Convenience route to filter posts by tag slug."""
    return redirect(url_for('blog.index', tag=slug))


@blog_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """
    Create a new blog post.
    Accessible only to authenticated users.
    """
    ensure_default_categories()

    form = PostForm()
    # Populate category dropdown choices dynamically
    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        title = form.title.data.strip()
        custom_slug = (form.slug.data or '').strip().lower()

        # Generate unique slug (or use custom slug validated for uniqueness)
        if custom_slug:
            slug = Post.generate_unique_slug(custom_slug)
        else:
            slug = Post.generate_unique_slug(title)

        # Process tags first before attaching to post
        post_tags_list = process_tags(form.tags.data)

        post = Post(
            title=title,
            slug=slug,
            content=form.content.data,
            category_id=form.category_id.data,
            author=current_user,
            tags=post_tags_list
        )

        db.session.add(post)
        db.session.commit()

        flash('Your blog post has been published successfully!', 'success')
        return redirect(url_for('blog.detail', slug=post.slug))

    return render_template('blog/create.html', form=form, categories=categories)


@blog_bp.route('/<slug>')
def detail(slug):
    """
    View an individual blog post by its unique slug.
    """
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('blog/view.html', post=post)


@blog_bp.route('/<slug>/edit', methods=['GET', 'POST'])
@login_required
def edit(slug):
    """
    Edit an existing blog post.
    Only the author of the post is permitted to edit.
    """
    post = Post.query.filter_by(slug=slug).first_or_404()

    # Enforce author authorization check
    if post.author.id != current_user.id:
        flash('You are not authorized to edit this post.', 'danger')
        abort(403)

    form = PostForm()
    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if request.method == 'GET':
        form.title.data = post.title
        form.slug.data = post.slug
        form.category_id.data = post.category_id
        form.tags.data = post.tag_names_str
        form.content.data = post.content

    if form.validate_on_submit():
        post_tags_list = process_tags(form.tags.data)
        post.title = form.title.data.strip()
        custom_slug = (form.slug.data or '').strip().lower()

        # Update slug if changed
        if custom_slug and custom_slug != post.slug:
            post.slug = Post.generate_unique_slug(custom_slug, post_id=post.id)
        elif not custom_slug and not post.slug:
            post.slug = Post.generate_unique_slug(post.title, post_id=post.id)

        post.category_id = form.category_id.data
        post.content = form.content.data
        post.updated_at = datetime.now(timezone.utc)
        post.tags = post_tags_list

        db.session.commit()
        flash('Your blog post has been updated successfully!', 'success')
        return redirect(url_for('blog.detail', slug=post.slug))

    return render_template('blog/edit.html', form=form, post=post, categories=categories)


@blog_bp.route('/<slug>/delete', methods=['POST'])
@login_required
def delete(slug):
    """
    Delete an existing blog post.
    Only the author of the post is permitted to delete.
    """
    post = Post.query.filter_by(slug=slug).first_or_404()

    # Enforce author authorization check
    if post.author.id != current_user.id:
        flash('You are not authorized to delete this post.', 'danger')
        abort(403)

    db.session.delete(post)
    db.session.commit()

    flash('The blog post has been deleted successfully.', 'info')
    return redirect(url_for('blog.index'))
