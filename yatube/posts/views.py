from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .models import Post, Group, Comment, Follow
from django.contrib.auth import get_user_model
from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required


Clip = 10
User = get_user_model()


def index(request):
    post_list = Post.objects.select_related('author', 'group')
    paginator = Paginator(post_list, Clip)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, Clip)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'group': group,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    follow_count = user.follower.all().count()
    followers_count = user.following.all().count()
    following = request.user.is_authenticated and \
        Follow.objects.filter(
            user=request.user,
            author=user
        ).exists()
    author_posts = user.posts.select_related('group', 'author')
    count = author_posts.count()
    paginator = Paginator(author_posts, Clip)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'author': user,
        'page_obj': page_obj,
        'count': count,
        'follow_count': follow_count,
        'followers_count': followers_count,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    comments = Comment.objects.select_related('post').filter(post=post)
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    title = 'Добавить запись'
    context = {
        'form': form,
        'title': title,
    }
    if form.is_valid():
        form = form.save(commit=False)
        form.author = request.user
        form.save()
        return redirect('posts:profile', request.user.username)
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, Clip)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'posts/follow.html',
        {'page_obj': page_obj, 'paginator': paginator}
    )


@login_required
def profile_follow(request, username):
    user = get_object_or_404(User, username=username)
    if user == request.user:
        return redirect(
            'posts:profile',
            username=username
        )
    follower = Follow.objects.filter(
        user=request.user,
        author=user
    ).exists()
    if follower is True:
        return redirect(
            'posts:profile',
            username=username
        )
    Follow.objects.create(user=request.user, author=user)
    return redirect(
        'posts:profile',
        username=username
    )


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if author == request.user:
        return redirect(
            'posts:profile',
            username=username
        )
    following = get_object_or_404(Follow, user=request.user, author=author)
    following.delete()
    return redirect(
        'posts:profile',
        username=username
    )
