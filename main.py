"""Web frontend for Scout profile lookup."""

from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from app.scrapers import (
    scrape_github,
    scrape_instagram,
    scrape_linktree,
    scrape_pinterest,
    scrape_tiktok,
    scrape_twitch,
    scrape_youtube,
)
from app.scrapers.linkedin import scrape_linkedin_profile

app = FastAPI(title="Scout")

PLATFORMS: dict[str, dict[str, Any]] = {
    "github": {"label": "GitHub", "hint": "username", "scrape": scrape_github},
    "twitch": {"label": "Twitch", "hint": "channel", "scrape": scrape_twitch},
    "youtube": {"label": "YouTube", "hint": "@handle", "scrape": scrape_youtube},
    "instagram": {"label": "Instagram", "hint": "username", "scrape": scrape_instagram},
    "tiktok": {"label": "TikTok", "hint": "username", "scrape": scrape_tiktok},
    "pinterest": {"label": "Pinterest", "hint": "username", "scrape": scrape_pinterest},
    "linktree": {"label": "Linktree", "hint": "username", "scrape": scrape_linktree},
    "linkedin": {"label": "LinkedIn", "hint": "profile slug", "scrape": scrape_linkedin_profile},
}

PRIMARY_FIELDS = [
    ("full_name", "Name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("website", "Website"),
    ("company", "Company"),
    ("location", "Location"),
    ("bio", "Bio"),
    ("follower_count", "Followers"),
    ("following_count", "Following"),
    ("subscriber_count", "Subscribers"),
    ("public_repos", "Public repos"),
    ("profile_url", "Profile"),
]


def _clean_username(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if "://" in value or value.startswith("www."):
        parsed = urlparse(value if "://" in value else f"https://{value}")
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            value = parts[-1]
    value = value.split("?")[0].split("#")[0].strip().lstrip("@")
    return value[:80]


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lookup")
def lookup(payload: dict[str, Any]) -> JSONResponse:
    platform = str(payload.get("platform") or "").strip().lower()
    username = _clean_username(str(payload.get("username") or ""))
    spec = PLATFORMS.get(platform)
    if spec is None:
        return JSONResponse({"ok": False, "error": "Pick a platform."}, status_code=400)
    if not username or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", username):
        return JSONResponse(
            {"ok": False, "error": "Enter a username, handle, or profile URL."},
            status_code=400,
        )

    scrape: Callable[..., Any] = spec["scrape"]
    try:
        profile = scrape(username)
    except Exception as exc:  # platform clients raise on network failures
        return JSONResponse(
            {"ok": False, "error": f"{spec['label']} did not respond: {exc}"},
            status_code=502,
        )

    if not profile:
        return JSONResponse(
            {
                "ok": False,
                "error": (
                    f"No public {spec['label']} profile came back for @{username}. "
                    "The account may be missing, private, or the platform blocked the request."
                ),
            },
            status_code=404,
        )

    return JSONResponse({"ok": True, "profile": _jsonable(profile)})


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Scout — public profile lookup</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,680&family=Outfit:wght@380;520;640&display=swap" rel="stylesheet" />
  <style>
    :root {
      --ink: #14090d;
      --panel: #221016;
      --line: rgba(255, 214, 224, 0.14);
      --text: #f8eef1;
      --muted: #c4a8b1;
      --accent: #e23d6b;
      --accent-deep: #a70947;
      --good: #d7f5c8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: Outfit, sans-serif;
      background:
        radial-gradient(900px 420px at 10% -10%, rgba(226, 61, 107, 0.28), transparent 60%),
        radial-gradient(700px 380px at 100% 0%, rgba(167, 9, 71, 0.35), transparent 55%),
        var(--ink);
    }
    main {
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 40px 0 64px;
    }
    header { display: flex; justify-content: space-between; gap: 16px; align-items: end; }
    h1 {
      margin: 0;
      font-family: Fraunces, serif;
      font-size: clamp(48px, 8vw, 84px);
      letter-spacing: -0.04em;
      line-height: 0.9;
    }
    .kicker { margin: 0 0 8px; color: var(--accent); font-weight: 640; letter-spacing: 0.14em; text-transform: uppercase; font-size: 12px; }
    p.lede { max-width: 46ch; color: var(--muted); font-size: 18px; line-height: 1.45; }
    .layout { display: grid; grid-template-columns: 320px 1fr; gap: 20px; margin-top: 28px; }
    .card {
      background: rgba(34, 16, 22, 0.86);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    select, input {
      width: 100%;
      border: 1px solid var(--line);
      background: #12080c;
      color: var(--text);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
    }
    .row { margin-bottom: 14px; }
    button {
      width: 100%;
      border: 0;
      border-radius: 999px;
      padding: 13px 16px;
      font: inherit;
      font-weight: 640;
      color: white;
      background: linear-gradient(180deg, var(--accent), var(--accent-deep));
      cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: wait; }
    .ghost {
      margin-top: 10px;
      background: transparent;
      color: var(--text);
      border: 1px solid var(--line);
    }
    .status { min-height: 220px; }
    .empty, .error { color: var(--muted); line-height: 1.5; }
    .error { color: #ffd0dc; }
    .who { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
    .who h2 { margin: 0; font-family: Fraunces, serif; font-size: 36px; letter-spacing: -0.03em; }
    .chip { color: var(--accent); font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }
    dl { display: grid; grid-template-columns: 140px 1fr; gap: 10px 14px; margin: 18px 0 0; }
    dt { color: var(--muted); }
    dd { margin: 0; overflow-wrap: anywhere; }
    a { color: var(--good); }
    .bio { grid-column: 1 / -1; }
    @media (max-width: 800px) {
      .layout, dl { grid-template-columns: 1fr; }
      header { display: block; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <p class="kicker">Scout</p>
        <h1>Look up a public profile.</h1>
      </div>
      <p class="lede">Paste a username or profile URL. Scout reads the public page and shows the name, bio, follower count, and any email or site already listed there.</p>
    </header>
    <div class="layout">
      <form class="card" id="lookup">
        <div class="row">
          <label for="platform">Platform</label>
          <select id="platform" name="platform">
            <option value="github">GitHub</option>
            <option value="twitch">Twitch</option>
            <option value="youtube">YouTube</option>
            <option value="instagram">Instagram</option>
            <option value="tiktok">TikTok</option>
            <option value="pinterest">Pinterest</option>
            <option value="linktree">Linktree</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </div>
        <div class="row">
          <label for="username">Username or URL</label>
          <input id="username" name="username" placeholder="torvalds" autocomplete="off" required />
        </div>
        <button id="go" type="submit">Look up</button>
        <button class="ghost" id="csv" type="button" hidden>Download this result as CSV</button>
      </form>
      <section class="card status" id="result">
        <p class="empty">Results land here. GitHub and Twitch are the most reliable starting points.</p>
      </section>
    </div>
  </main>
  <script>
    const form = document.getElementById("lookup");
    const result = document.getElementById("result");
    const go = document.getElementById("go");
    const csv = document.getElementById("csv");
    let latest = null;

    const labels = {
      full_name: "Name", email: "Email", phone: "Phone", website: "Website",
      company: "Company", location: "Location", bio: "Bio", follower_count: "Followers",
      following_count: "Following", public_repos: "Public repos", profile_url: "Profile",
      is_verified: "Verified", is_private: "Private", is_partner: "Partner",
      is_affiliate: "Affiliate", is_hireable: "Hireable"
    };

    function cell(value) {
      if (value == null || value === "" || value === false) return "";
      if (Array.isArray(value)) return value.map(item => typeof item === "string" ? item : (item.url || JSON.stringify(item))).join(" | ");
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    }

    function escapeHtml(value) {
      return cell(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[char]));
    }

    function render(profile) {
      const skip = new Set(["platform", "username"]);
      const rows = Object.entries(profile).filter(([key, value]) => !skip.has(key) && cell(value));
      const body = rows.map(([key, value]) => {
        const text = cell(value);
        const safe = escapeHtml(text);
        const shown = /^https?:\\/\\//.test(text) ? `<a href="${safe}" target="_blank" rel="noreferrer">${safe}</a>` : safe;
        return `<dt>${labels[key] || key}</dt><dd class="${key === "bio" ? "bio" : ""}">${shown}</dd>`;
      }).join("");
      result.innerHTML = `<div class="who"><h2>${escapeHtml(profile.full_name || profile.username)}</h2><span class="chip">${escapeHtml(profile.platform || "")}</span></div><dl>${body}</dl>`;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      go.disabled = true;
      go.textContent = "Looking up…";
      csv.hidden = true;
      result.innerHTML = `<p class="empty">Fetching the public profile…</p>`;
      try {
        const response = await fetch("/api/lookup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            platform: document.getElementById("platform").value,
            username: document.getElementById("username").value
          })
        });
        const data = await response.json();
        if (!data.ok) {
          latest = null;
          result.innerHTML = `<p class="error">${escapeHtml(data.error || "Lookup failed.")}</p>`;
          return;
        }
        latest = data.profile;
        render(latest);
        csv.hidden = false;
      } catch (error) {
        latest = null;
        result.innerHTML = `<p class="error">The lookup did not finish. Try again in a moment.</p>`;
      } finally {
        go.disabled = false;
        go.textContent = "Look up";
      }
    });

    csv.addEventListener("click", () => {
      if (!latest) return;
      const keys = Object.keys(latest);
      const line = keys.map(key => `"${cell(latest[key]).replaceAll('"', '""')}"`).join(",");
      const blob = new Blob([keys.join(",") + "\\n" + line + "\\n"], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${latest.platform || "scout"}-${latest.username || "profile"}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    });
  </script>
</body>
</html>
"""
