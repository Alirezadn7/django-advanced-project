from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Category, Post, Tag

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with sample Persian blog posts, categories, and tags."

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample blog data...")

        # 1. Ensure an author user exists
        author = User.objects.filter(is_staff=True).first()
        if not author:
            author = User.objects.filter(email="admin@blog.ir").first()
            if not author:
                author = User.objects.create_superuser(
                    email="admin@blog.ir",
                    password="adminpassword123",
                )
                self.stdout.write(self.style.SUCCESS(f"Created author: {author.email} (Password: adminpassword123)"))
        else:
            self.stdout.write(f"Using existing user: {author.email}")

        # Ensure user profile has a nice display name
        if hasattr(author, "profile"):
            profile = author.profile
            profile.first_name = "تیم"
            profile.last_name = "مهندسی جنگو"
            profile.bio = "متخصص مهندسی نرم‌افزار، توسعه‌دهنده ارشد پایتون و علاقه‌مند به معماری سیستم‌های توزیع‌شده."
            profile.save()

        # 2. Categories
        cat_django, _ = Category.objects.get_or_create(
            name="آموزش جنگو و پایتون",
            defaults={"slug": "django-python"}
        )
        cat_devops, _ = Category.objects.get_or_create(
            name="معماری نرم‌افزار و DevOps",
            defaults={"slug": "software-architecture-devops"}
        )
        cat_security, _ = Category.objects.get_or_create(
            name="امنیت و احراز هویت",
            defaults={"slug": "security-auth"}
        )

        # 3. Tags
        tags_dict = {}
        tags_data = [
            ("جنگو", "django"),
            ("داکر", "docker"),
            ("پایتون", "python"),
            ("احراز هویت", "auth"),
            ("JWT", "jwt"),
            ("پیام‌رسان بله", "bale-messenger"),
            ("REST API", "rest-api"),
        ]
        for name, slug in tags_data:
            tag_obj, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slug})
            tags_dict[slug] = tag_obj

        # 4. Posts
        posts_data = [
            {
                "title": "راهنمای جامع پیاده‌سازی ورود بدون رمز عبور با OTP پیام‌رسان بله در جنگو",
                "slug": "passwordless-otp-login-bale-django",
                "category": cat_security,
                "tags": [tags_dict["auth"], tags_dict["bale-messenger"], tags_dict["django"]],
                "content": """در این مقاله به بررسی یکی از امن‌ترین و مدرن‌ترین روش‌های احراز هویت کاربران یعنی ورود بدون پسورد (Passwordless) با استفاده از کد یکبارمصرف (OTP) ارسالی در پیام‌رسان بله می‌پردازیم.

### چرا احراز هویت مبتنی بر پیام‌رسان؟
استفاده از پیامک‌های مخابراتی (SMS) به دلیل تاخیر در تحویل، هزینه‌های بالا و آسیب‌پذیری‌های امنیتی همواره چالش‌برانگیز بوده است. درگاه Safir پیام‌رسان بله این امکان را فراهم می‌آورد تا کدهای تایید در کسری از ثانیه و با ضریب امنیت بالا مستقیماً به حساب کاربری کاربر در پیام‌رسان تحویل داده شوند.

### اصول امنیتی ذخیره‌سازی OTP
یکی از اشتباهات رایج در سیستم‌های احراز هویت، ذخیره خام کد ارسالی در دیتابیس است. در این پروژه، کد تولیدی هرگز ذخیره نمی‌شود، بلکه هش SHA-256 همراه با نمک (Salt) در دیتابیس قرار می‌گیرد:
- زمان انقضای محدود (معمولاً ۲ دقیقه)
- محدودیت سقف تلاش (حداکثر ۵ بار تلاش ناموفق)
- کنترل نرخ بر اساس شماره تلفن (Rate Limiting) جهت پیشگیری از حملات Brute-Force

پس از تایید موفق کد OTP، یک جفت توکن JWT (Access و Refresh) تولید شده و جلسه کاربر با بالاترین استاندارد امنیتی آغاز می‌گردد.""",
            },
            {
                "title": "کانتینرسازی برنامه‌های جنگو با Docker و Docker Compose در محیط توسعه و عملیات",
                "slug": "dockerizing-django-applications-docker-compose",
                "category": cat_devops,
                "tags": [tags_dict["docker"], tags_dict["django"]],
                "content": """کانتینرسازی (Containerization) یکی از استانداردهای اساسی در مهندسی نرم‌افزار مدرن است که معضل کلاسیک «روی سیستم من کار می‌کرد!» را برای همیشه حل کرده است.

### ساختار Dockerfile بهینه
در طراحی یک داکرفایل استاندارد برای فریم‌ورک جنگو، باید نکات زیر رعایت شوند:
1. استفاده از متغیرهای `PYTHONDONTWRITEBYTECODE=1` و `PYTHONUNBUFFERED=1` جهت جلوگیری از نوشتن فایل‌های کش غیرضروری و دریافت لاگ‌های فوری در کنسول.
2. تفکیک کپی کردن فایل `requirements.txt` و نصب وابستگی‌ها پیش از کپی کل کدها تا از سیستم کش لایه‌های داکر نهایت استفاده به عمل آید.
3. تنظیم `PYTHONPATH` برای تشخیص صحیح پکیج‌ها و اپلیکیشن‌ها در ساختارهای تودرتو.

### استفاده از Docker Compose برای هماهنگی سرویس‌ها
با کمک `docker-compose.yml` می‌توان سرویس‌های جانبی نظیر دیتابیس PostgreSQL، ردیس (Redis) و وب‌سرور Nginx را تنها با یک دستور `docker compose up` بالا آورد. در پروژه فعلی، پورت ۸۰۰۰ داخلی کانتینر روی پورت ۹۰۰۰ ماشین میزبان مپ شده و ولوم برای بارگذاری زنده تغییرات کد متصل شده است.""",
            },
            {
                "title": "معماری طراحی REST API تمیز و استاندارد با Django REST Framework",
                "slug": "clean-rest-api-architecture-drf",
                "category": cat_django,
                "tags": [tags_dict["django"], tags_dict["rest-api"], tags_dict["jwt"]],
                "content": """فریم‌ورک Django REST Framework (DRF) یکی از قدرتمندترین ابزارها برای ساخت وب‌سرویس‌های مقیاس‌پذیر در اکوسیستم پایتون است.

### استفاده از ViewSet و Router
یکی از بهترین الگوهای DRY در DRF، استفاده از `ModelViewSet` همراه با `DefaultRouter` است. این الگو باعث می‌شود که تمام عملیات استاندارد CRUD (ایجاد، خواندن، ویرایش، حذف) به همراه صفحه‌بندی و فیلترینگ بدون نوشتن کدهای تکراری تعریف شوند.

### مدیریت دسترسی‌ها (Permissions)
تعریف مجوزهای سفارشی نظیر `IsAuthorOrReadOnly` تضمین می‌کند که کاربران ناشناس تنها به خواندن مقالات دسترسی دارند، در حالی که ویرایش و حذف تنها توسط نویسنده همان مقاله قابل انجام است.

همچنین، استفاده از `django-filter` و جستجوی چندفیلدی به کاربران API این امکان را می‌دهد تا مقالات را بر اساس دسته‌بندی، نویسنده و وضعیت انتشار فیلتر کنند.""",
            },
            {
                "title": "بهترین الگوهای طراحی ساختار تنظیمات و ماژول‌ها در پروژه‌های سازمانی جنگو",
                "slug": "best-practices-settings-modules-django",
                "category": cat_django,
                "tags": [tags_dict["django"], tags_dict["python"]],
                "content": """در پروژه‌های بزرگ و پیشرفته، قرار دادن تمام تنظیمات در یک فایل واحد `settings.py` باعث پیچیدگی و خطاهای عملیاتی می‌شود.

### تفکیک تنظیمات Development و Production
بهترین الگو برای مدیریت تنظیمات:
- فایل `base.py`: تنظیمات مشترک نظیر اپلیکیشن‌های نصب‌شده، میان‌افزارها و زبان پروژه.
- فایل `development.py`: تنظیمات مخصوص توسعه محلی با دیتابیس سبک SQLite و حالت Debug فعال.
- فایل `production.py`: تنظیمات امنیتی بالا، کلید‌های محافظت‌شده، سرور پایگاه داده اصلی و مدیریت کش.

با استفاده از کتابخانه‌هایی نظیر `python-decouple`، متغیرهای حساس محیطی از طریق فایل `.env` خوانده می‌شوند و هرگز در مخزن گیت ذخیره نخواهند شد.""",
            },
        ]

        now = timezone.now()
        for pdata in posts_data:
            post, created = Post.objects.get_or_create(
                slug=pdata["slug"],
                defaults={
                    "title": pdata["title"],
                    "content": pdata["content"],
                    "author": author,
                    "category": pdata["category"],
                    "is_published": True,
                    "published_date": now,
                }
            )
            if created:
                post.tags.set(pdata["tags"])
                post.save()
                self.stdout.write(self.style.SUCCESS(f"Created post: {pdata['slug']}"))
            else:
                self.stdout.write(f"Post already exists: {pdata['slug']}")

        self.stdout.write(self.style.SUCCESS("All sample data seeded successfully!"))
