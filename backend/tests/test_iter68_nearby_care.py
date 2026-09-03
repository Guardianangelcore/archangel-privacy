# Iter 68 — Nearby Care locator (/api/nearby/care): tier gate + live OSM results.
import os, subprocess, requests, pytest

B = os.environ.get("TEST_API", "http://localhost:8001/api")


def _tok(email, tier):
    t = requests.post(f"{B}/auth/dev-bypass", json={"email": email, "name": "T"}).json()["session_token"]
    subprocess.run(["mongosh", "--quiet", "guardian_health", "--eval",
                    f'db.users.updateOne({{email:"{email}"}},{{$set:{{tier:"{tier}"}}}})'], capture_output=True)
    return {"Authorization": f"Bearer {t}"}


def test_sovereign_gets_402():
    r = requests.get(f"{B}/nearby/care?kind=pharmacy&lat=48.1486&lng=17.1077", headers=_tok("nc-sov@test.sk", "sovereign"))
    assert r.status_code == 402
    assert "guardian_required" in str(r.json())


def test_bad_kind_400():
    r = requests.get(f"{B}/nearby/care?kind=vet&lat=48.1&lng=17.1", headers=_tok("nc-g@test.sk", "guardian"))
    assert r.status_code == 400


@pytest.mark.parametrize("kind", ["pharmacy", "doctor", "emergency"])
def test_guardian_gets_sorted_results(kind):
    r = requests.get(f"{B}/nearby/care?kind={kind}&lat=48.1486&lng=17.1077&radius=3000",
                     headers=_tok("nc-g@test.sk", "guardian"), timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["kind"] == kind and d["center"]["lat"] == 48.1486
    res = d["results"]
    assert len(res) > 0
    assert all({"name", "lat", "lng", "distance_km", "opening_hours"} <= set(x) for x in res)
    assert res == sorted(res, key=lambda x: x["distance_km"])
    assert res[0]["distance_km"] < 3.5
