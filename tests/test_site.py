"""Builds the blog with Hugo and checks the rendered output, the way a visitor sees it.

Run: python3 -m unittest discover tests
"""
import json
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

    def test_live_site_is_indexable(self):
        for path in ("index.html", "posts/griz/index.html"):
            self.assertNotIn("noindex", read(path))

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


class Timeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, result = build_posts({"day.md": post("[Other]", (
            "{{< timeline >}}\n1. **Wake up.** We walk. [Walk](#1-walk)\n"
            "2. **Dinner.** They eat.\n{{< /timeline >}}\n\n## 1. Walk"))})
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        with open(os.path.join(cls.tmp, "public/posts/day/index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def test_is_an_ordered_list_of_stops(self):
        day = re.search(r'<div class="k9-timeline">(.*?)</div>', self.html, re.S).group(1)
        self.assertEqual(day.count("<li>"), 2)
        self.assertIn("<ol>", day)
        self.assertIn('href="#1-walk"', day)

    def test_stops_are_searchable(self):
        with open(os.path.join(self.tmp, "public/index.json"), encoding="utf-8") as f:
            self.assertIn("Wake up. We walk.", json.load(f)[0]["body"])


class CategoryRule(unittest.TestCase):
    def test_build_fails_without_exactly_one_known_category(self):
        for categories in ("[]", "[Gear, Dogs]", "[Cats]"):
            with self.subTest(categories=categories):
                tmp, result = build_posts({"bad.md": post(categories)})
                shutil.rmtree(tmp, ignore_errors=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("exactly one Category", result.stdout + result.stderr)


class Feed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        posts = {f"gear-{i:02}.md": post("[Gear]", f"Gear body {i}. {'word ' * 120}").replace(
            "2026-01-02", f"2026-01-{i:02}") for i in range(1, 15)}
        posts["dog.md"] = post("[Dogs]", "{{< youtube cFSE0V6iDTQ >}}\n\nShe wouldn't stop.").replace(
            "2026-01-02", "2026-02-01")
        cls.tmp, result = build_posts(posts)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def built(self, path):
        with open(os.path.join(self.tmp, "public", path), encoding="utf-8") as f:
            return f.read()

    def cards(self, path):
        return re.findall(r'<article class="k9-card">.*?</article>', self.built(path), re.S)

    def test_newest_first_twelve_then_the_rest(self):
        first, second = self.cards("index.html"), self.cards("page/2/index.html")
        self.assertEqual((len(first), len(second)), (12, 3))
        self.assertIn('href="/posts/dog/"', first[0])
        self.assertIn('href="/posts/gear-14/"', first[1])
        self.assertIn('href="/posts/gear-01/"', second[-1])

    def test_card_contents(self):
        card = self.cards("index.html")[0]
        self.assertIn("i.ytimg.com/vi/cFSE0V6iDTQ/", card)
        self.assertIn('href="/categories/dogs/"', card)
        self.assertIn('href="/tags/e-collar/"', card)
        for expected in ("A Test Post", "February 1, 2026", "She wouldn’t stop."):
            self.assertIn(expected, text(card))
        self.assertNotIn("Play video", card)

    def test_more_loads_on_scroll_and_is_a_link_without_js(self):
        more = re.search(r'<a [^>]*class="[^"]*k9-more[^>]*>', self.built("index.html")).group(0)
        self.assertIn('href="/page/2/"', more)
        self.assertIn('hx-get="/page/2/"', more)
        self.assertIn('href="/"', self.built("page/2/index.html"))

    def test_search_gets_a_quoted_index_url(self):
        self.assertIn("""x-data="k9Search('/index.json')\"""", self.built("index.html"))

    def test_chips_hide_empty_categories(self):
        chips = re.search(r'<nav class="k9-chips".*?</nav>', self.built("index.html"), re.S).group(0)
        self.assertEqual(text(chips), "All Gear Dogs")

    def test_category_and_tag_pages_are_feeds(self):
        self.assertEqual(len(self.cards("categories/dogs/index.html")), 1)
        self.assertEqual(len(self.cards("tags/recall/index.html")), 12)

    def test_index_works_for_search_and_the_chat_agent(self):
        pages = json.loads(self.built("index.json"))
        self.assertEqual(len(pages), 15)
        dog = pages[0]
        self.assertEqual(dog["url"], "https://griz.sh/posts/dog/")
        self.assertEqual(dog["tags"], ["recall", "e-collar"])
        self.assertEqual(dog["category"], "Dogs")
        self.assertIn('class="k9-card"', dog["card"])
        self.assertNotIn("youtube", dog["summary"])
        for p in pages:
            self.assertLessEqual(len(p["summary"]), 401)
            self.assertNotIn("&rsquo;", p["summary"])
        self.assertGreater(len(pages[1]["body"]), 400)


class Comments(unittest.TestCase):
    def setUp(self):
        self.html = read("posts/griz/index.html")

    def test_every_post_has_list_and_form(self):
        for slug in os.listdir(os.path.join(PUBLIC, "posts")):
            if os.path.isdir(os.path.join(PUBLIC, "posts", slug)) and slug != "page":
                html = read(f"posts/{slug}/index.html")
                self.assertIn('id="comments"', html, slug)
                self.assertIn('id="commentForm"', html, slug)

    def test_keyed_by_path_and_only_approved_shown(self):
        self.assertIn("postSlug: {eq: window.location.pathname}, approved: {eq: true}", self.html)
        self.assertIn("postSlug: window.location.pathname", self.html)

    def test_reader_text_is_escaped(self):
        self.assertIn("{{name}}", self.html)
        self.assertIn("{{comment}}", self.html)
        self.assertNotIn("{{{", self.html)

    def test_posting_needs_turnstile(self):
        self.assertIn('class="cf-turnstile"', self.html)
        self.assertIn("x-turnstile-token", self.html)

    def test_only_posts_load_comment_scripts(self):
        self.assertIn("challenges.cloudflare.com", self.html)
        self.assertNotIn("challenges.cloudflare.com", read("index.html"))


class NotFound(unittest.TestCase):
    def test_404_links_to_the_feed(self):
        html = read("404.html")
        main = re.search(r"<main>(.*?)</main>", html, re.S).group(1)
        self.assertIn('href="/"', main)


class SeedPosts(unittest.TestCase):
    def setUp(self):
        self.posts = {p["url"].rstrip("/").rsplit("/", 1)[-1]: p for p in json.loads(read("index.json"))}

    def test_seeds_are_in_their_categories(self):
        seeds = {
            "Gear": ["agitation-collar", "e-collar", "flat-collar", "prong-collar", "slip-collar"],
            "Dogs": ["griz", "denali", "odie"],
            "Training": ["food-and-play", "escape-and-avoidance"],
            "Food": ["what-my-dogs-eat"],
            "Other": ["dogs-need-enrichment"],
        }
        for category, slugs in seeds.items():
            for slug in slugs:
                with self.subTest(slug=slug):
                    self.assertEqual(self.posts[slug]["category"], category)
                    self.assertRegex(read(f"posts/{slug}/index.html").split("<main>")[1].split("</main>")[0],
                                     r'href="?https://k9-communication\.com/')

    def test_enrichment_has_the_walk(self):
        self.assertIn("cFSE0V6iDTQ", read("posts/dogs-need-enrichment/index.html"))

    def test_enrichment_has_a_day_and_eight_things_it_links_to(self):
        html = read("posts/dogs-need-enrichment/index.html")
        self.assertIn('class="k9-timeline"', html)
        things = re.findall(r'<h2 id="?([1-8]-[^">]+)', html)
        self.assertEqual([t[0] for t in things], list("12345678"))
        self.assertEqual(set(re.findall(r'href="#([1-8]-[^"]+)"', html)), set(things))

    def test_enrichment_card_shows_the_walk(self):
        self.assertIn("cFSE0V6iDTQ", self.posts["dogs-need-enrichment"]["card"])

    def test_agitation_collar_does_not_claim_protection_training(self):
        self.assertIn("I don’t train protection", text(read("posts/agitation-collar/index.html")))


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
