from django.db.models import Count, Q
from django.views.generic import DetailView, ListView

from .models import Category, Post, Tag


class BlogListView(ListView):
    """
    Public web view for listing published blog posts with search,
    category & tag filtering, and pagination.
    """
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 6

    def get_queryset(self):
        queryset = (
            Post.objects.filter(is_published=True)
            .select_related('author', 'category')
            .prefetch_related('tags')
            .order_by('-published_date', '-created_date')
        )

        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(tags__name__icontains=query)
            ).distinct()

        category_slug = self.request.GET.get('category', '').strip()
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        tag_slug = self.request.GET.get('tag', '').strip()
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Annotate post counts for published posts only
        context['categories'] = Category.objects.annotate(
            post_count=Count('post', filter=Q(post__is_published=True))
        ).order_by('name')

        context['popular_tags'] = (
            Tag.objects.annotate(
                post_count=Count('post', filter=Q(post__is_published=True))
            )
            .filter(post_count__gt=0)
            .order_by('-post_count')[:15]
        )

        category_slug = self.request.GET.get('category', '').strip()
        if category_slug:
            context['active_category'] = Category.objects.filter(slug=category_slug).first()

        tag_slug = self.request.GET.get('tag', '').strip()
        if tag_slug:
            context['active_tag'] = Tag.objects.filter(slug=tag_slug).first()

        context['search_query'] = self.request.GET.get('q', '').strip()

        # Featured latest post (only on first page when not filtering by search)
        page = self.request.GET.get('page')
        if not page or page == '1':
            if not context['search_query'] and not category_slug and not tag_slug:
                all_published = context['posts']
                if all_published:
                    context['featured_post'] = all_published[0]

        return context


class BlogDetailView(DetailView):
    """
    Public web view displaying a single blog post by its slug.
    """
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Staff can view drafts; public users only published posts
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return Post.objects.select_related('author', 'category').prefetch_related('tags')
        return (
            Post.objects.filter(is_published=True)
            .select_related('author', 'category')
            .prefetch_related('tags')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Estimate reading time (approx 200 words per minute)
        word_count = len(post.content.split()) if post.content else 0
        context['reading_time'] = max(1, round(word_count / 180))

        # Related posts based on category or tags
        related = Post.objects.filter(is_published=True).exclude(id=post.id)
        if post.category:
            related_category = related.filter(category=post.category)
            if related_category.exists():
                related = related_category

        context['related_posts'] = (
            related.select_related('author', 'category')
            .order_by('-published_date')[:3]
        )

        return context

