#!/usr/bin/env python3
"""Збирає сайт із src/*: index.html (одна сторінка), 404.html, robots.txt, sitemap.xml, site.webmanifest.

    python build.py                          # локальна збірка: усе закрито від індексації (noindex)
    python build.py https://autopolish.com.ua  # бойова збірка для свого домену: canonical, sitemap, Open Graph

Адресу сайту можна також задати в site.json ("site_url") або змінною середовища SITE_URL.
Картинки та іконки готує tools/make_assets.py (потрібен Pillow); build.py використовує тільки стандартну бібліотеку.
"""
import datetime
import html
import json
import os
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent
src = root / 'src'
sys.path.insert(0, str(src))
import content as C  # noqa: E402

rd = lambda n: (src / n).read_text(encoding='utf-8')
esc = lambda s: html.escape(s, quote=True)


# ------------------------------------------------------------------ налаштування
def load_config():
    cfg = {'site_url': '', 'demo_notice': True, 'google_verification': '', 'bing_verification': ''}
    f = root / 'site.json'
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding='utf-8')))
    if os.environ.get('SITE_URL'):
        cfg['site_url'] = os.environ['SITE_URL']
    if len(sys.argv) > 1 and sys.argv[1].strip():
        cfg['site_url'] = sys.argv[1]
    u = (cfg['site_url'] or '').strip().rstrip('/')
    if u and not re.fullmatch(r'https?://[A-Za-z0-9.\-]+(:\d+)?', u):
        sys.exit('Адреса сайту має вигляд https://example.com.ua (без шляху й пробілів), а не: %r' % u)
    cfg['site_url'] = u
    return cfg


CFG = load_config()
S = CFG['site_url']
B = C.BUSINESS
MAPS = re.search(r"MAPS_URL:\s*'([^']+)'", rd('app.js')).group(1)
TODAY = datetime.date.today().isoformat()
CSS = rd('style.css')
PHONE_HTML = B['phone_fmt'].replace(' ', '&nbsp;')
FONTS = 'https://fonts.googleapis.com/css2?family=Geologica:wght@500;700;800&family=Onest:wght@400;500;600&display=swap'
HERO_SIZES = '(max-width: 960px) 100vw, 740px'


def render(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace('{{%s}}' % k, v)
    left = re.findall(r'\{\{\w+\}\}', tpl)
    assert not left, left
    return tpl


# ------------------------------------------------------------------ <head>
def jsonld(obj):
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def business_node(full=True):
    n = {
        '@type': 'AutomotiveBusiness',
        '@id': S + '/#business',
        'name': B['name'],
        'alternateName': B['brand'],
        'telephone': B['phone'],
        'address': {'@type': 'PostalAddress', 'streetAddress': B['street'], 'addressLocality': B['city'],
                    'addressRegion': B['region'], 'addressCountry': B['country']},
    }
    if full:
        n.update({
            'url': S + '/',
            'image': S + '/images/og.jpg',
            'logo': S + '/icon-512.png',
            'description': 'Детейлінг-студія в Дніпрі: полірування кузова, керамічне покриття, хімчистка салону, полірування фар, антигравійна плівка.',
            'geo': {'@type': 'GeoCoordinates', 'latitude': B['lat'], 'longitude': B['lng']},
            'hasMap': MAPS,
            'areaServed': {'@type': 'City', 'name': B['city']},
            'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification', 'dayOfWeek': B['work_days'], 'opens': B['open'], 'closes': B['close']}],
            'sameAs': [B['instagram']],
            'knowsLanguage': 'uk',
            'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Послуги', 'itemListElement': [
                {'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': n, 'areaServed': B['city']}} for n in C.SERVICE_NAMES]},
        })
    return n


def head(title, desc, path, ld=None, hero=False, indexable=True):
    url = S + path if S else ''
    live = bool(S) and indexable
    h = ['<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
         '<title>%s</title>' % esc(title),
         '<meta name="description" content="%s">' % esc(desc),
         '<meta name="robots" content="%s">' % ('index, follow, max-image-preview:large, max-snippet:-1' if live else 'noindex, nofollow'),
         '<meta name="theme-color" content="#F1F2EF">',
         '<meta name="color-scheme" content="light">']
    if live:
        h += ['<link rel="canonical" href="%s">' % url,
              '<link rel="alternate" hreflang="uk" href="%s">' % url,
              '<link rel="alternate" hreflang="x-default" href="%s">' % url]
    h += ['<meta property="og:type" content="website">', '<meta property="og:locale" content="uk_UA">',
          '<meta property="og:site_name" content="%s">' % esc(B['brand']),
          '<meta property="og:title" content="%s">' % esc(title), '<meta property="og:description" content="%s">' % esc(desc)]
    if live:
        h += ['<meta property="og:url" content="%s">' % url,
              '<meta property="og:image" content="%s/images/og.jpg">' % S,
              '<meta property="og:image:type" content="image/jpeg">',
              '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
              '<meta property="og:image:alt" content="AutoPolish — детейлінг у Дніпрі">',
              '<meta name="twitter:card" content="summary_large_image">',
              '<meta name="twitter:title" content="%s">' % esc(title), '<meta name="twitter:description" content="%s">' % esc(desc),
              '<meta name="twitter:image" content="%s/images/og.jpg">' % S]
    if CFG['google_verification']:
        h.append('<meta name="google-site-verification" content="%s">' % esc(CFG['google_verification']))
    if CFG['bing_verification']:
        h.append('<meta name="msvalidate.01" content="%s">' % esc(CFG['bing_verification']))
    h += ['<link rel="icon" href="/favicon.ico" sizes="any">',
          '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
          '<link rel="icon" href="/favicon-48.png" type="image/png" sizes="48x48">',
          '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
          '<link rel="manifest" href="/site.webmanifest">']
    if hero:
        h.append('<link rel="preload" as="image" href="/images/hero-1200.webp" imagesrcset="/images/hero-800.webp 800w, /images/hero-1200.webp 1200w, '
                 '/images/hero-1600.webp 1600w" imagesizes="%s" fetchpriority="high">' % HERO_SIZES)
    # шрифти не блокують відмальовування: спершу системний шрифт, потім Geologica/Onest
    h += ['<link rel="preconnect" href="https://fonts.googleapis.com">',
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
          '<link rel="stylesheet" href="%s" media="print" onload="this.media=\'all\'">' % FONTS,
          '<noscript><link rel="stylesheet" href="%s"></noscript>' % FONTS]
    if live and ld:
        h.append(jsonld(ld))
    return '\n'.join(h)


# ------------------------------------------------------------------ спільні шматки
def hours_rows():
    rows = []
    for i, (k, uk) in enumerate(C.DAYS_UK):
        rows.append('<tr data-d="%s"><th scope="row">%s</th><td>%s</td></tr>' % (k, uk, '%s–%s' % (B['open'], B['close']) if i < 5 else 'Зачинено'))
    return ''.join(rows)


def footer():
    f = ['<footer>', '<div class="wrap">',
         '<span><span translate="no">%s</span> · %s, %s</span>' % (esc(B['brand']), esc(B['street']), esc(B['city']))]
    if CFG['demo_notice']:
        f.append('<span>Демонстраційна сторінка за публічними даними Google Maps. Це не офіційний сайт студії. Фото в галереї: картка студії на Google Maps.</span>')
    f += ['</div>', '</footer>']
    return '\n'.join(f)


COMMON = dict(css=CSS, maps=MAPS, phone=B['phone'], phone_html=PHONE_HTML, street=esc(B['street']), city=esc(B['city']),
              instagram=B['instagram'], hours_rows=hours_rows(), footer=footer())

def home_page():
    js = rd('app.js') + '\n})();'
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebSite', '@id': S + '/#website', 'url': S + '/', 'name': 'AutoPolish Дніпро', 'inLanguage': 'uk',
         'publisher': {'@id': S + '/#business'}},
        business_node()]}
    page = render(rd('template.html'), head=head(C.HOME['title'], C.HOME['desc'], '/', ld, hero=True), js=js,
                  h1=esc(C.HOME['h1']), sub=esc(C.HOME['sub']), hero_sizes=HERO_SIZES, **COMMON)
    (root / 'index.html').write_text(page, encoding='utf-8')
    return page


def not_found():
    page = render(rd('404.html'), head=head('Сторінку не знайдено — AutoPolish', 'Такої сторінки немає.', '/404.html', indexable=False), **COMMON)
    (root / '404.html').write_text(page, encoding='utf-8')


def robots_and_sitemap(paths):
    if S:
        (root / 'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: %s/sitemap.xml\n' % S, encoding='utf-8')
        imgs = ['/images/hero-1600.webp'] + ['/images/gallery-%d.webp' % i for i in range(1, 8)]
        rows = []
        for p in paths:
            extra = ''.join('<image:image><image:loc>%s%s</image:loc></image:image>' % (S, i) for i in imgs)
            rows.append('  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority>%s</url>' % (
                S, p, TODAY, 'monthly', '1.0' if p == '/' else '0.8', extra))
        (root / 'sitemap.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n%s\n</urlset>\n' % '\n'.join(rows), encoding='utf-8')
    else:  # без домену закриваємо від індексації, щоб тестова копія не потрапила в пошук
        (root / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
        if (root / 'sitemap.xml').exists():
            (root / 'sitemap.xml').unlink()


def manifest():
    m = {'name': 'AutoPolish Дніпро — детейлінг', 'short_name': 'AutoPolish', 'lang': 'uk', 'start_url': '/', 'display': 'browser',
         'background_color': '#F1F2EF', 'theme_color': '#F1F2EF',
         'icons': [{'src': '/icon-192.png', 'sizes': '192x192', 'type': 'image/png'}, {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png'}]}
    (root / 'site.webmanifest').write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


# ------------------------------------------------------------------ збірка
home = home_page()
not_found()
robots_and_sitemap(['/'])
manifest()

if len(C.HOME['title']) > 66 or len(C.HOME['desc']) > 160:
    print('  УВАГА: title %d, description %d симв. (Google обрізає довші)' % (len(C.HOME['title']), len(C.HOME['desc'])))
print('Режим: %s' % (('бойовий, %s' % S) if S else 'локальний (noindex): задайте домен — python build.py https://ваш-домен'))
print('index.html %d байт' % len(home.encode('utf-8')))
