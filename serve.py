"""Локальний сервер для сайту AutoPolish + передача заявок у Telegram. Без бази даних: нічого не зберігається.

Запуск:  python serve.py [порт]      (порт за замовчуванням 8080)

Токен бота живе тільки тут, на сервері, у файлі telegram_token.txt поруч зі скриптом
(або в змінній середовища TELEGRAM_BOT_TOKEN). У код сторінки він не потрапляє.
chat_id майстра зберігається в telegram.json після першого /start боту.
Підключити/змінити акаунт можна лише з паролем (файл telegram_password.txt): надіслати боту /start ПАРОЛЬ.
/stop у чаті майстра відключає його без пароля.
"""
import base64, functools, hmac, html, http.server, ipaddress, json, os, re, secrets, socket, sys, threading, time, urllib.error, urllib.request, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, os.environ.get("AP_SITE", "site-v5"))
STATIC_LONG = {".webp", ".jpg", ".jpeg", ".png", ".svg", ".ico", ".woff", ".woff2", ".webmanifest"}
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TG_API = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")
TOKEN_FILE = os.path.join(HERE, "telegram_token.txt")
PASS_FILE = os.path.join(HERE, "telegram_password.txt")
CFG_FILE = os.path.join(HERE, "telegram.json")
TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")
MAX_BODY = 40 * 1024 * 1024
MIN_FILL_MS = int(os.environ.get("AP_MIN_FILL_MS", "3000"))  # швидше за це людина форму не заповнить: далі це бот
MAX_PHOTO = 10 * 1024 * 1024

state = {"token": "", "chat_id": None, "bot": "", "error": "", "pw": ""}
fails = {}   # chat_id -> часи невдалих спроб пароля
gfails = []  # усі невдалі спроби (захист від перебору з багатьох акаунтів)
lock = threading.Lock()


# ---------------------------------------------------------------- config
def load_token():
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not t and os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8-sig") as f:
            t = f.read()
    t = t.strip()
    return t if TOKEN_RE.match(t) else ""


def read_cfg():
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load_chat():
    env = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if env:
        return int(env)
    try:
        return int(read_cfg().get("chat_id"))
    except Exception:
        return None


def save_chat(chat_id):  # єдине, що запам'ятовується: чат майстра, куди слати заявки (None = нікого не підключено)
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump({"chat_id": chat_id}, f)


PW_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"  # без схожих символів (0/O, 1/l/I)
PW_MIN = 12


def pw_norm(p):
    return re.sub(r"[\s\-_]", "", p or "")


def load_password():
    """Пароль підключення Telegram-акаунта: telegram_password.txt (або TELEGRAM_PASSWORD). Якщо його немає чи він
    занадто короткий, створюється випадковий і записується у файл."""
    p = os.environ.get("TELEGRAM_PASSWORD", "")
    if not p and os.path.exists(PASS_FILE):
        with open(PASS_FILE, "r", encoding="utf-8-sig") as f:
            p = f.read()
    p = p.strip()
    if len(pw_norm(p)) < PW_MIN:
        weak = bool(p)
        p = "-".join("".join(secrets.choice(PW_ALPHABET) for _ in range(4)) for _ in range(4))
        with open(PASS_FILE, "w", encoding="utf-8") as f:
            f.write(p)
        print("  Пароль підключення %s: див. файл telegram_password.txt" % ("замінено на надійніший (старий був закороткий)" if weak else "створено"))
    return p


# ---------------------------------------------------------------- telegram api
def tg_json(method, payload, timeout=30):
    req = urllib.request.Request(
        "%s/bot%s/%s" % (TG_API, state["token"], method),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return _tg_send(req, timeout)


def tg_multipart(method, fields, files, timeout=60):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode("utf-8")
    for name, (filename, data, ctype) in files.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (boundary, name, filename, ctype)).encode("utf-8")
        body += data + b"\r\n"
    body += ("--%s--\r\n" % boundary).encode("utf-8")
    req = urllib.request.Request(
        "%s/bot%s/%s" % (TG_API, state["token"], method),
        data=bytes(body),
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    return _tg_send(req, timeout)


def _tg_send(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8"))
        except Exception:
            j = {"ok": False, "description": "HTTP %s" % e.code}
    except Exception as e:  # network down, timeout
        raise RuntimeError("Telegram недоступний: %s" % e)
    if not j.get("ok"):
        raise RuntimeError(j.get("description", "Telegram error"))
    return j["result"]


# ---------------------------------------------------------------- setup: хто отримує заявки
ENV_CHAT = bool(os.environ.get("TELEGRAM_CHAT_ID", "").strip())  # чат заданий ззовні: з Telegram його не змінити


def say(chat_id, text):
    try:
        tg_json("sendMessage", {"chat_id": chat_id, "text": text})
    except Exception:
        pass


def check_password(cid, given):
    """True/False; None, якщо забагато невдалих спроб (блокування на 15 хвилин, навіть для правильного пароля)."""
    now = time.time()
    with lock:
        win = [t for t in fails.get(cid, []) if now - t < 900]
        gfails[:] = [t for t in gfails if now - t < 900]
        if len(win) >= 5 or len(gfails) >= 20:
            fails[cid] = win
            return None
        good = hmac.compare_digest(pw_norm(given).encode("utf-8"), pw_norm(state["pw"]).encode("utf-8"))
        if not good:
            win.append(now)
            gfails.append(now)
        fails[cid] = win
        return good


def handle_message(m):
    """Керування підключенням з самого Telegram (лише приватні чати).
    Пароль (/start ПАРОЛЬ, /connect ПАРОЛЬ або просто пароль окремим повідомленням) робить цей акаунт отримувачем
    і замінює попереднього. /stop відключає, може лише поточний отримувач."""
    chat = m.get("chat") or {}
    if chat.get("type") != "private":
        return
    cid, mid = chat.get("id"), m.get("message_id")
    raw = str(m.get("text", "")).strip()
    parts = raw.split(None, 1)
    cmd = parts[0].lower().split("@")[0] if raw.startswith("/") else ""
    arg = parts[1].strip() if cmd and len(parts) > 1 else ""
    owner = state["chat_id"] == cid
    if cmd == "/stop":
        with lock:
            if owner and not ENV_CHAT:
                state["chat_id"] = None
                save_chat(None)
        if owner and ENV_CHAT:
            say(cid, "Цей чат заданий налаштуванням сервера (TELEGRAM_CHAT_ID), з Telegram його не змінити.")
        elif owner:
            say(cid, "⏸ Відключено: заявки більше не надходять. Щоб підключити акаунт, надішліть боту /start і пароль підключення.")
            print("  Telegram: чат відключено командою /stop.")
        else:
            say(cid, "Ця команда доступна лише підключеному акаунту.")
        return
    if cmd and cmd not in ("/start", "/connect"):
        return
    if cmd and not arg:  # /start без пароля
        if owner:
            say(cid, "✅ Уже підключено: заявки приходять сюди.\nЩоб відключити, надішліть /stop.")
        else:
            say(cid, "Щоб отримувати заявки, надішліть пароль підключення одним повідомленням.")
        return
    if not cmd and owner:  # звичайна розмова підключеного власника з ботом
        return
    if ENV_CHAT and not owner:
        say(cid, "Підключення змінити не можна: чат заданий налаштуванням сервера.")
        return
    ok = check_password(cid, arg if cmd else raw)
    try:  # пароль не лишаємо в історії чату
        if mid is not None:
            tg_json("deleteMessage", {"chat_id": cid, "message_id": mid})
    except Exception:
        pass
    if ok is None:
        say(cid, "Забагато невдалих спроб. Спробуйте через 15 хвилин.")
    elif not ok:
        say(cid, "Невірний пароль.")
    else:
        with lock:
            old = state["chat_id"]
            state["chat_id"] = cid
            save_chat(cid)
        if old == cid:
            say(cid, "✅ Уже підключено: заявки приходять сюди.")
        else:
            say(cid, "✅ Підключено. Нові заявки з сайту приходитимуть сюди.\nЩоб відключити, надішліть /stop.")
            if old is not None:
                say(old, "Заявки передано іншому акаунту. Щоб повернути їх сюди, надішліть боту /start і пароль підключення.")
            print("  Telegram: заявки тепер надходять у новий чат.")


def setup_thread():
    try:
        me = tg_json("getMe", {})
        state["bot"] = me.get("username", "")
    except Exception as e:
        state["error"] = str(e)
        print("  Telegram: токен не підійшов (%s)" % e)
        return
    print("  Telegram: бот @%s підключено." % state["bot"])
    try:
        tg_json("setMyCommands", {"commands": [{"command": "stop", "description": "Відключити цей акаунт від заявок"}]})
    except Exception:
        pass
    if state["chat_id"] is None:
        print("  Відкрийте https://t.me/%s, надішліть /start і пароль з файлу telegram_password.txt: туди почнуть приходити заявки." % state["bot"])
    offset = 0
    while True:  # слухаємо команди весь час, щоб підключення можна було змінити без редагування файлів
        try:
            ups = tg_json("getUpdates", {"offset": offset, "timeout": 25, "allowed_updates": ["message"]}, timeout=40)
        except Exception:
            time.sleep(5)
            continue
        for u in ups:
            offset = u["update_id"] + 1
            try:
                handle_message(u.get("message") or {})
            except Exception as e:
                print("  Telegram: помилка команди: %s" % e)


# ---------------------------------------------------------------- order -> message
def esc(v):
    return html.escape(str(v or "").strip(), quote=False)


def clip(v, n):
    return str(v or "").strip()[:n]


def build_message(o):
    lines = ["🆕 <b>Заявка %s</b>" % esc(clip(o.get("id"), 20)), ""]
    lines.append("👤 <b>%s</b>" % esc(clip(o.get("name"), 80)))
    lines.append("📞 %s" % esc(clip(o.get("phone"), 40)))
    lines.append("💬 Відповісти: %s" % esc(clip(o.get("via"), 40)))
    lines.append("")
    car = esc(clip(o.get("car"), 80))
    cls = esc(clip(o.get("cls"), 40))
    lines.append("🚗 %s%s" % (car, " · " + cls if cls else ""))
    svc = o.get("svc") or []
    lines.append("🔧 %s" % esc(", ".join(clip(s, 60) for s in svc[:10])))
    lines.append("📅 %s" % esc(clip(o.get("when"), 80)))
    if clip(o.get("note"), 500):
        lines.append("📝 %s" % esc(clip(o.get("note"), 500)))
    n = len(o.get("photos") or [])
    if n:
        lines.append("📷 Фото: %d" % n)
    return "\n".join(lines)


def decode_photos(o):
    out = []
    for p in (o.get("photos") or [])[:10]:
        m = re.match(r"^data:image/(jpeg|png|webp);base64,(.+)$", str(p), re.S)
        if not m:
            continue
        data = base64.b64decode(m.group(2))
        if len(data) <= MAX_PHOTO:
            out.append((m.group(1), data))
    return out


ID_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_id():
    """Номер заявки без лічильника й сховища: день+місяць і три випадкові символи, напр. AP-1911-K7Q."""
    return "AP-%s-%s" % (time.strftime("%d%m"), "".join(secrets.choice(ID_CHARS) for _ in range(3)))


def deliver(o):
    """Одразу передає заявку майстру в Telegram. Повертає номер заявки."""
    if not state["token"]:
        raise RuntimeError("Бот не налаштовано: немає telegram_token.txt")
    if state["chat_id"] is None:
        raise RuntimeError("Майстер ще не натиснув Start у боті @%s" % (state["bot"] or "…"))
    o["id"] = new_id()
    _deliver(o)
    return o["id"]


def _deliver(o):
    payload = {"chat_id": state["chat_id"], "text": build_message(o), "parse_mode": "HTML", "disable_web_page_preview": True}
    digits = re.sub(r"\D", "", str(o.get("phone") or ""))
    if str(o.get("via")) == "Telegram" and 10 <= len(digits) <= 13:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": "Написати в Telegram", "url": "https://t.me/+" + digits}]]}
    msg = tg_json("sendMessage", payload)
    photos = decode_photos(o)
    if len(photos) == 1:
        ext, data = photos[0]
        tg_multipart("sendPhoto", {"chat_id": state["chat_id"], "reply_to_message_id": msg["message_id"]}, {"photo": ("photo." + ext, data, "image/" + ext)})
    elif photos:
        media = [{"type": "photo", "media": "attach://p%d" % i} for i in range(len(photos))]
        files = {"p%d" % i: ("photo%d.%s" % (i + 1, e), d, "image/" + e) for i, (e, d) in enumerate(photos)}
        tg_multipart("sendMediaGroup", {"chat_id": state["chat_id"], "reply_to_message_id": msg["message_id"], "media": json.dumps(media)}, files)


# ---------------------------------------------------------------- захист від спаму
RATE_IP, RATE_PHONE, RATE_ALL, RATE_WINDOW = 10, 5, 100, 3600  # заявок за годину: з однієї адреси, з одного телефону, усього
hits = {}


def rate_count(key):
    now = time.time()
    with lock:
        hits[key] = [t for t in hits.get(key, []) if now - t < RATE_WINDOW]
        return len(hits[key])


def rate_add(key):
    with lock:
        hits.setdefault(key, []).append(time.time())


def is_local(ip):
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback
    except ValueError:
        return False


URL_RE = re.compile(r"https?://|www\.|t\.me/", re.I)


def looks_like_bot(o):
    """Ознаки бота: заповнене приховане поле, форма надіслана швидше, ніж це може зробити людина, посилання в імені/авто."""
    if str(o.get("hp") or "").strip():
        return "приховане поле"
    if MIN_FILL_MS > 0:
        try:
            if float(o.get("t")) < MIN_FILL_MS:
                return "занадто швидко"
        except (TypeError, ValueError):
            return "без таймера форми"
    if URL_RE.search(str(o.get("name") or "") + " " + str(o.get("car") or "")):
        return "посилання в імені"
    if len(URL_RE.findall(str(o.get("note") or ""))) > 1:
        return "багато посилань"
    return ""


# ---------------------------------------------------------------- http
def telegram_ready():
    return bool(state["token"] and state["chat_id"] is not None)


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_response(self, code, message=None):
        self._code = code
        super().send_response(code, message)

    def end_headers(self):
        # Локально віддаємо завжди свіжу збірку (no-store). У бойовому режимі (AP_PROD=1) статика кешується:
        # сторінки на 5 хвилин, картинки/іконки/шрифти на тиждень, що пришвидшує сайт і враховується пошуковиками.
        cache = "no-store"
        if os.environ.get("AP_PROD") == "1" and getattr(self, "_code", 0) in (200, 304) and not self.path.startswith("/api/"):
            ext = os.path.splitext(self.path.split("?")[0])[1].lower()
            cache = "public, max-age=604800" if ext in STATIC_LONG else "public, max-age=300"
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def guess_type(self, path):
        t = super().guess_type(path)
        if t.startswith("text/") or t in ("application/json", "application/xml", "application/manifest+json"):
            t += "; charset=utf-8"  # кирилиця в HTML/XML/JSON відображається правильно навіть без <meta charset>
        return t

    def send_error(self, code, message=None, explain=None):
        # власна сторінка 404 (з посиланнями на головну й форму запису), якщо вона є в збірці
        page = os.path.join(ROOT, "404.html")
        if code == 404 and self.command in ("GET", "HEAD") and os.path.isfile(page):
            with open(page, "rb") as f:
                body = f.read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command == "GET":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/status":
            return self._json(200, {"telegram": telegram_ready()})
        if path == "/favicon.ico" and not os.path.isfile(os.path.join(ROOT, "favicon.ico")):  # немає файлу — порожня відповідь замість 404
            self.send_response(204)
            self.end_headers()
            return
        return super().do_GET()

    def client_ip(self):
        ip = self.client_address[0]
        xff = self.headers.get("X-Forwarded-For", "")
        if ip in ("127.0.0.1", "::1") and xff:  # за reverse proxy (Caddy) справжня адреса клієнта лежить тут
            ip = xff.split(",")[0].strip()
        return ip

    def do_POST(self):
        if self.path.split("?")[0] != "/api/order":
            return self._json(404, {"ok": False, "error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._json(413, {"ok": False, "error": "bad size"})
            o = json.loads(self.rfile.read(n).decode("utf-8"))
            digits = re.sub(r"\D", "", str(o.get("phone") or "")) if isinstance(o, dict) else ""
            if (not isinstance(o, dict) or not str(o.get("name", "")).strip() or len(str(o.get("name"))) > 80
                    or not 9 <= len(digits) <= 15):
                return self._json(400, {"ok": False, "error": "bad order"})
            why = looks_like_bot(o)
            if why:  # боту показуємо «успіх», щоб він не підбирав обхід; майстру нічого не надходить
                print("  Спам відхилено (%s)." % why)
                return self._json(200, {"ok": True, "id": new_id()})
            ip = self.client_ip()
            # локальна мережа (тести, ПК майстра) без обмежень; для публічних адрес: ліміти за адресою, телефоном і загальний
            keys = [] if is_local(ip) else [("all", RATE_ALL), ("phone:" + digits, RATE_PHONE), ("ip:" + ip, RATE_IP)]
            if any(rate_count(k) >= lim for k, lim in keys):
                print("  Забагато заявок (%s), відхилено." % ip)
                return self._json(429, {"ok": False, "error": "too many"})
            oid = deliver(o)
            for k, _ in keys:
                rate_add(k)
            print("  Заявка %s надіслана майстру." % oid)
            return self._json(200, {"ok": True, "id": oid})
        except Exception as e:
            print("  Помилка заявки: %s" % e)
            return self._json(502, {"ok": False, "error": str(e)})

    def log_message(self, fmt, *args):
        # не засмічуємо консоль запитами до API; args[0] буває не рядком (HTTPStatus), тому дивимось на шлях запиту
        if str(getattr(self, "path", "")).startswith("/api/"):
            return
        super().log_message(fmt, *args)


def lan_ips():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips)


if __name__ == "__main__":
    state["token"] = load_token()
    state["chat_id"] = load_chat()
    if state["token"]:
        state["pw"] = load_password()
    handler = functools.partial(Handler, directory=ROOT)
    # на Windows SO_REUSEADDR дозволяє двом серверам зайняти один порт: вимикаємо, щоб зайнятий порт був помітний
    http.server.ThreadingHTTPServer.allow_reuse_address = (os.name != "nt")
    srv = None
    for port in range(PORT, PORT + 10):
        try:
            srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
            break
        except OSError:
            continue
    if srv is None:
        print("Не вдалося зайняти жоден порт %d-%d. Закрийте старі вікна сервера і запустіть ще раз." % (PORT, PORT + 9))
        sys.exit(1)
    if port != PORT:
        print("УВАГА: порт %d зайнятий (імовірно, старе вікно сервера). Закрийте його, а цей сервер відкривайте за адресою нижче." % PORT)
    PORT = port
    print("AutoPolish: сайт працює")
    print("  На цьому ПК:  http://localhost:%d/" % PORT)
    for ip in lan_ips():
        print("  З телефона:   http://%s:%d/  (та сама Wi-Fi мережа)" % (ip, PORT))
    if state["token"]:
        threading.Thread(target=setup_thread, daemon=True).start()
    else:
        print("  УВАГА: немає telegram_token.txt — заявки не буде кому надсилати. Покладіть токен бота в цей файл і перезапустіть сервер.")
    print("Щоб зупинити, закрийте це вікно або натисніть Ctrl+C.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
