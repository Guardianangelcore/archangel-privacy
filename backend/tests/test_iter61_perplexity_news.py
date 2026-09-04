# Iter 61 — Perplexity live news & briefing integration tests
import os, time, uuid, requests, pytest

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://physio-lang-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
FOUNDER_EMAIL = "guardianangel.core@proton.me"


def _bypass(email, name="X"):
    r = requests.post(f"{API}/auth/dev-bypass", json={"email": email, "name": name}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def founder_token():
    return _bypass(FOUNDER_EMAIL, "Guardian Angel")


@pytest.fixture(scope="module")
def fresh_token():
    return _bypass(f"iter61-fresh-{uuid.uuid4().hex[:8]}@example.com", "Iter61 Fresh")


# ---------- /api/news/feed ----------

def _hdr(tok): return {"Authorization": f"Bearer {tok}"}


def test_news_feed_unauth():
    r = requests.get(f"{API}/news/feed", timeout=20)
    assert r.status_code == 401


def test_news_feed_founder(founder_token):
    t0 = time.time()
    r = requests.get(f"{API}/news/feed", headers=_hdr(founder_token), timeout=30)
    dt = time.time() - t0
    assert r.status_code == 200, r.text
    d = r.json()
    assert dt < 8.0, f"feed too slow: {dt:.1f}s"
    assert d.get("live") is True, f"expected live=True (warm cache): {d.get('note')}"
    assert d.get("engine") == "Perplexity Sonar · sonar-pro"
    assert d.get("fetched_at"), "fetched_at required when live"
    assert isinstance(d.get("personalized"), list)
    assert isinstance(d.get("general"), list)
    assert len(d["general"]) >= 3, f"expected ≥3 general items, got {len(d['general'])}"
    # Personal items may be [] if focus empty — but founder has warm personal per playbook
    # Validate item shape on general
    for n in d["general"]:
        assert n["news_id"].startswith("live-"), n["news_id"]
        assert n["title"] and n["summary"]
        assert "[1]" not in n["summary"] and "**" not in n["summary"]
        assert n["url"].startswith("http")
        assert isinstance(n["tags"], list)
        assert n["live"] is True
        assert isinstance(n["high_tech"], bool)
        assert n["region"] and n["specialty"] and n["source"]
    # personalized items (if any) must have jarvis_alert & matched=True
    for n in d.get("personalized", []):
        assert n["matched"] is True
        assert n["matched_tags"], "matched_tags must be non-empty"
        assert isinstance(n["jarvis_alert"], str) and n["jarvis_alert"]


def test_news_feed_fresh_user_poll(fresh_token):
    t0 = time.time()
    r = requests.get(f"{API}/news/feed", headers=_hdr(fresh_token), timeout=30)
    assert r.status_code == 200, r.text
    dt = time.time() - t0
    assert dt < 8.0, f"first feed too slow: {dt:.1f}s"
    d = r.json()
    # Either warm cache reused (live true) or pending + curated seed
    if not d["live"]:
        assert d["pending"] is True
        assert d["general"], "curated seed must be present as fallback"
        # curated items have n-... news_id
        assert any(n["news_id"].startswith("n-") for n in d["general"])
        assert "Fetching" in d.get("note", "") or "live" in d.get("note", "").lower()
    # Poll up to 90s
    deadline = time.time() + 90
    live = d["live"]
    while not live and time.time() < deadline:
        time.sleep(10)
        r = requests.get(f"{API}/news/feed", headers=_hdr(fresh_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        live = d["live"]
    if not live:
        pytest.skip("Perplexity did not return within 90s (likely 429 rate limit) — acceptable degradation")
    assert d["engine"] == "Perplexity Sonar · sonar-pro"
    assert len(d["general"]) >= 3


def test_news_feed_force(founder_token):
    r = requests.get(f"{API}/news/feed?force=true", headers=_hdr(founder_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    # force may pass through pending; live could still be True from cache within LIVE_FORCE_MIN
    assert isinstance(d.get("live"), bool)


# ---------- /api/news/{id}/hunt ----------

def test_news_hunt_unknown(founder_token):
    r = requests.post(f"{API}/news/does-not-exist/hunt", headers=_hdr(founder_token), timeout=20)
    assert r.status_code == 404


def test_news_hunt_live_item(founder_token):
    r = requests.get(f"{API}/news/feed", headers=_hdr(founder_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    all_items = (d.get("personalized") or []) + (d.get("general") or [])
    target = next((n for n in all_items if n.get("hunt_city")), None)
    if not target:
        pytest.skip("No live item with hunt_city in current cache")
    r = requests.post(f"{API}/news/{target['news_id']}/hunt", headers=_hdr(founder_token), timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert body.get("message")
    wl = body.get("waitlist_item")
    assert wl and wl.get("item_id") and wl.get("city") == target["hunt_city"]


# ---------- /api/news/tech-tracker ----------

def test_tech_tracker(founder_token):
    r = requests.get(f"{API}/news/tech-tracker", headers=_hdr(founder_token), timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d.get("deployments"), list)
    assert d.get("hunter_note")


# ---------- /api/agent/briefing ----------

def test_agent_briefing_founder(founder_token):
    r = requests.get(f"{API}/agent/briefing?force=true", headers=_hdr(founder_token), timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d.get("briefing"), str) and d["briefing"]
    news = d.get("news")
    assert isinstance(news, list) and len(news) <= 3
    if news:
        assert d.get("news_engine") == "Perplexity Sonar · sonar-pro"
        for n in news:
            assert n["title"] and n["url"].startswith("http")
            assert "source" in n and "summary" in n
    else:
        # acceptable if 429 rate limit (news_engine None)
        assert d.get("news_engine") in (None, "Perplexity Sonar · sonar-pro")

    # 2nd call without force → cache
    r2 = requests.get(f"{API}/agent/briefing", headers=_hdr(founder_token), timeout=30)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("news") == news


# ---------- /api/agent/search (regression) ----------

def test_agent_search_founder(founder_token):
    r = requests.post(f"{API}/agent/search",
                      json={"query": "ECDC influenza vaccination guidance 2026"},
                      headers=_hdr(founder_token), timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("reply")
    if d.get("degraded"):
        pytest.skip("Perplexity degraded (429 or key issue) — acceptable")
    assert d.get("live_search") is True
    assert isinstance(d.get("citations"), list) and len(d["citations"]) >= 1
