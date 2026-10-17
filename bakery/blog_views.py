from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import BlogCategory, BlogPost


def published_posts():
    return BlogPost.objects.filter(is_published=True, published_at__lte=timezone.now()).select_related("category", "product")


def blog(request):
    posts = published_posts()
    categories = BlogCategory.objects.filter(posts__in=posts).distinct()
    selected_category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()[:200]
    if selected_category:
        posts = posts.filter(category__slug=selected_category)
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(body__icontains=query))
    featured = None
    if not selected_category and not query and request.GET.get("page", "1") == "1":
        featured = posts.filter(is_featured=True).first() or posts.first()
    page = Paginator(posts, 9).get_page(request.GET.get("page"))
    return render(request, "bakery/blog.html", {
        "page": page, "featured": featured, "categories": categories,
        "selected_category": selected_category, "query": query,
    })


def blog_detail(request, slug):
    post = get_object_or_404(published_posts(), slug=slug)
    related = published_posts().exclude(pk=post.pk)
    if post.category_id:
        related = related.filter(category_id=post.category_id)
    recipe = post.product if post.product_id and post.product.recipe_instructions else None
    return render(request, "bakery/blog_detail.html", {
        "post": post, "related_posts": related[:3], "recipe": recipe,
        "recipe_items": recipe.recipe_items.select_related("ingredient") if recipe else (),
    })
