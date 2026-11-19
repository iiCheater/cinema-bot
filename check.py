import requests, json, os, re, sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup

TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
FILE = "seen.json"


def get(url):
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def scene():
    url = "https://cfc.scenecinemas.com/home"
    movies = {}
    for a in get(url).select('a[href*="/movie-details/"]'):
        name = a.get("title") or a.get_text(strip=True)
        if name:
            movies[a["href"]] = (name, urljoin(url, a["href"]))
    return movies


def elcinema():
    # كل الأفلام المعروضة في سينمات مصر (VOX, Galaxy, Premiere, ...)
    movies = {}
    for page in range(1, 11):
        new = 0
        for a in get(f"https://elcinema.com/now/eg/?page={page}").select('h3 a[href*="/work/"]'):
            m = re.search(r"/work/(\d+)/?$", a["href"])
            name = a.get_text(strip=True)
            if m and name:
                link = f"https://elcinema.com/work/{m.group(1)}/"
                if link not in movies:
                    movies[link] = (name, link)
                    new += 1
        if not new:
            break
    return movies


# (الاسم اللي يظهر في الرسالة، علامة تميّز لينكات المصدر، الدالة)
SOURCES = [
    ("Scene Cinemas CFC", "/movie-details/", scene),
    ("سينمات مصر (elcinema)", "elcinema.com", elcinema),
]

seen = set(json.load(open(FILE))) if os.path.exists(FILE) else set()
ok = 0

for label, marker, fn in SOURCES:
    try:
        movies = fn()
    except Exception as e:
        print(label, "- فشل:", e)
        continue
    print(label, "- لقيت", len(movies), "فيلم")
    if not movies:
        continue
    ok += 1
    # أول مرة للمصدر ده: سجّل الأفلام الحالية من غير رسايل
    first_time = not any(marker in key for key in seen)
    if not first_time:
        for key in movies.keys() - seen:
            name, link = movies[key]
            requests.get(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                params={"chat_id": CHAT_ID, "text": f"🎬 فيلم جديد: {name}\n{label}\n{link}"},
            )
    seen |= set(movies)

json.dump(sorted(seen), open(FILE, "w"), ensure_ascii=False)

if not ok:
    sys.exit("مفيش أفلام اتقرأت من أي مصدر")
