from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Post, Group, Follow
from .forms import PostForm, CommentForm
from django.views.decorators.cache import cache_page


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html',
                  {'page': page, 'paginator': paginator})


def group_posts(request, slug):
    """view-функция для страницы сообщества"""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.group.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "group.html",
                  {'group': group, 'page': page, 'paginator': paginator})


@login_required
def new_post(request):
    """view-функция для добавления новых записей если пользователь залогинен"""
    title = "Новая запись"
    button = "Опубликовать"
    if request.method != 'POST':
        # данные не отправлялись; создается пустая форма.
        form = PostForm()
        return render(request, "new.html", {'form': form, 'button': button,
                                            'title': title})
    form = PostForm(request.POST, files=request.FILES or None)
    if not form.is_valid():
        return render(request, "new.html", {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect("index")


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    count = posts.count()
    following = Follow.objects.filter(author=author).exists()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'profile.html',
        {'page': page, 'paginator': paginator, 'count': count,
         'posts': posts, 'author': author, 'following': following}
    )


def post_view(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    comments = post.comments.all()
    author = post.author
    count = author.posts.count()
    form = CommentForm()
    return render(request, 'post.html',
                  {'form': form, 'count': count, 'post': post,
                   'author': author, 'comments': comments})


def post_edit(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    button = "Редактировать"
    title = "Редактировать запись"
    if post.author != request.user:
        return redirect("post", username=username, post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=post)
    if not form.is_valid():
        return render(request, 'new.html', {'form': form, 'post': post,
                                            'button': button,
                                            'title': title})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect("post", username=username, post_id=post_id)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect("post", username=username, post_id=post_id)
    return render(request, 'includes/comments.html', {'form': form, 'post': post,
                                             'comments': comments})


@login_required
def follow_index(request):
    fav_posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(fav_posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'follow.html',
                  {'page': page, 'paginator': paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = User.objects.get(username=request.user)
    if not request.user.follower.filter(author=author).exists() and\
            user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    user = User.objects.get(username=request.user)
    following = Follow.objects.filter(user=user, author=author).delete()
    return redirect('profile', username=username)


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)