# Store Reviewer Access — Archangel OS

Paste the block below into:
* **App Store Connect** → your app version → **App Review Information** → *Sign-In required* → Demo Account
* **Google Play Console** → **App content** → **App access** (Sign-in details)

---

```
Demo account for review
Email:    appreview@archangel-os.app
Password: <current REVIEWER_PASSWORD from backend/.env>

Steps
1. Open the app.
2. On the login screen keep the "SIGN IN" tab selected.
3. Enter the e-mail and password above and tap SIGN IN.
4. The account holds a permanent reviewer entitlement (ARCHANGEL plan) granted
   server-side. No purchase, promo code, MFA, OTP or device pairing is required.
5. All subscription-gated features are reachable immediately (Jarvis AI, Bunker Mode,
   Offline Mesh, Bio-Scanner, Digital Twin, Life Card, Family Shield).
6. Sample data is pre-loaded: Life Card (vaccinations, surgeries, lab results, an AI
   prediction), a completed waitlist hunt, a €150 refund claim and one family contact.

Purchases: the subscription screen shows real store products (RevenueCat). Reviewers do
NOT need to purchase anything — the demo account is already entitled.

Emergency features: SOS / Family Shield send real SMS only after a contact is added by
the user. The pre-loaded demo contact is a non-routable placeholder number.
```

---

## Operations

* Credentials live **only** in `backend/.env` (`REVIEWER_EMAIL`, `REVIEWER_PASSWORD`).
  Nothing is hardcoded in the repository or shipped in the mobile bundle.
* The account is re-verified on every backend boot (`backend/reviewer_seed.py`):
  entitlement and sample data are refreshed, the password hash is **never** silently
  changed.
* **Rotate the password** (recommended after each review cycle):
  1. set a new `REVIEWER_PASSWORD` (≥16 chars) in `backend/.env`
  2. set `REVIEWER_ROTATE_PASSWORD=true`
  3. restart the backend (all reviewer sessions are revoked)
  4. set `REVIEWER_ROTATE_PASSWORD=false` again and update the store submission notes.
* The account is deliberately **not** privileged: no `is_founder`, no `inner_circle`, so
  the Foundation admin surfaces (Partner Approval Panel, Wealth Dashboard, Demo Mode)
  return 403 for it.
* Do **not** document the Founder account or the founder-only Demo Mode endpoint in store
  notes.


## Google Play — Data safety › "Data deletion" URL
Public page (no sign-in): `https://<your-deployed-domain>/delete-account`
Describes both paths: in-app (Profile → DELETE ACCOUNT & ALL DATA, immediate) and the e-mail request form
(processed by the Founder within 30 days via Profile-less API queue). What is erased vs. retained is listed on the page.
