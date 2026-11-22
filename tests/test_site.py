"""Builds the blog with Hugo and checks the rendered output, the way a visitor sees it.

Run: python3 -m unittest discover tests
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def setUpModule():
    global PUBLIC
    PUBLIC = tempfile.mkdtemp(prefix="k9-blog-")
    subprocess.run(["hugo", "--quiet", "--panicOnWarning", "-d", PUBLIC], cwd=ROOT, check=True)


def tearDownModule():
    shutil.rmtree(PUBLIC, ignore_errors=True)


def read(path):
    with open(os.path.join(PUBLIC, path.lstrip("/")), encoding="utf-8") as f:
        return f.read()


def text(html):
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


class Scaffold(unittest.TestCase):
    def setUp(self):
        self.html = read("index.html")

    def test_title(self):
        title = re.search(r"<title>(.*?)</title>", self.html, re.S).group(1)
        self.assertEqual(text(title), "K9-Communication LLC’s Blog")

    def test_header_has_logo_and_links_to_business_site(self):
        header = re.search(r"<header>(.*?)</header>", self.html, re.S).group(1)
        self.assertIn('src="/images/logo.png"', header)
        self.assertIn('href="https://k9-communication.com/"', header)

    def test_canonical_is_griz_sh(self):
        self.assertIn('<link rel="canonical" href="https://griz.sh/">', self.html)

    def test_no_chatbot(self):
        self.assertNotIn("k9-chat", self.html)

    def test_theme_matches_business_site(self):
        css = read(re.search(r'<link rel="stylesheet" href="(/[^"]+\.css)"', self.html).group(1))
        for token in ("--k9-pine", "--k9-mauve", "--k9-gold", "Barlow Condensed"):
            self.assertIn(token, css)

    def test_robots_points_to_sitemap(self):
        self.assertIn("Sitemap: https://griz.sh/sitemap.xml", read("robots.txt"))


def build_posts(posts):
    """Builds the blog with these Posts ({path: front matter and body}) as its only content."""
    tmp = tempfile.mkdtemp(prefix="k9-blog-posts-")
    for path, source in posts.items():
        full = os.path.join(tmp, "content", "posts", path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(source)
    result = subprocess.run(
        ["hugo", "--panicOnWarning", "--contentDir", os.path.join(tmp, "content"),
         "-d", os.path.join(tmp, "public")],
        cwd=ROOT, capture_output=True, text=True)
    return tmp, result


def post(categories, body="Body."):
    return (f'---\ntitle: "A Test Post"\ndate: 2026-01-02\ncategories: {categories}\n'
            f'tags: [recall, e-collar]\n---\n\n{body}\n')


class PostPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, result = build_posts({
            "flat.md": post("[Gear]", "{{< youtube cFSE0V6iDTQ >}}"),
            "nested/deep.md": post("[Dogs]"),
        })
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        with open(os.path.join(cls.tmp, "public/posts/flat/index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_url_is_flat(self):
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "public/posts/deep/index.html")))

    def test_shows_title_date_category_and_tags(self):
        body = text(re.search(r"<main>(.*?)</main>", self.html, re.S).group(1))
        for expected in ("A Test Post", "January 2, 2026", "Gear", "recall", "e-collar"):
            self.assertIn(expected, body)

    def test_youtube_loads_on_tap_and_links_out_without_js(self):
        self.assertNotIn("<iframe", self.html)
        self.assertIn('href="https://www.youtube.com/watch?v=cFSE0V6iDTQ"', self.html)
        self.assertIn('src="https://i.ytimg.com/vi/cFSE0V6iDTQ/hqdefault.jpg"', self.html)
        self.assertIn("youtube-nocookie.com/embed/", self.html)


class CategoryRule(unittest.TestCase):
    def test_build_fails_without_exactly_one_known_category(self):
        for categories in ("[]", "[Gear, Dogs]", "[Cats]"):
            with self.subTest(categories=categories):
                tmp, result = build_posts({"bad.md": post(categories)})
                shutil.rmtree(tmp, ignore_errors=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("exactly one Category", result.stdout + result.stderr)


class NotFound(unittest.TestCase):
    def test_404_links_to_the_feed(self):
        html = read("404.html")
        main = re.search(r"<main>(.*?)</main>", html, re.S).group(1)
        self.assertIn('href="/"', main)


class Links(unittest.TestCase):
    def test_internal_links_and_anchors_resolve(self):
        broken = set()
        for root, _, files in os.walk(PUBLIC):
            for name in files:
                if not name.endswith(".html"):
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    for href in re.findall(r'href="(/[^"]*)"', f.read()):
                        path, _, frag = href.partition("#")
                        target = os.path.join(PUBLIC, path.lstrip("/"))
                        if os.path.isdir(target):
                            target = os.path.join(target, "index.html")
                        if not os.path.exists(target):
                            broken.add(href)
                        elif frag and target.endswith(".html"):
                            with open(target, encoding="utf-8") as t:
                                if f'id="{frag}"' not in t.read():
                                    broken.add(href)
        self.assertEqual(broken, set())


if __name__ == "__main__":
    unittest.main()
