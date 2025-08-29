
# ingestion/article_fetcher_playwright.py (v2.2) — headless-hardening + debug + auto-head on challenge
from __future__ import annotations
import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple

from dotenv import load_dotenv
load_dotenv()

from playwright.sync_api import sync_playwright

DEFAULT_SELECTOR = ".meteredContent"
DESKTOP_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _parse_cookie_header(cookie_header: str) -> List[Tuple[str,str]]:
    parts = [p.strip() for p in cookie_header.split(";") if p.strip()]
    cookies = []
    for p in parts:
        if "=" in p:
            name, value = p.split("=", 1)
            cookies.append((name.strip(), value.strip()))
    return cookies

def _clean_text(text: str) -> str:
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"(\n\s*){3,}", "\n\n", text)
    noise = [
        r"^\s*(home|about|contact|subscribe|login|sign\s?in|sign\s?up|get started)\s*$",
        r"^\s*(share|follow|menu|search|privacy|terms|cookies|advertising)\s*$",
        r"^\s*(©|copyright)\s+\d{4}",
        r"^\s*\d+\s+min(read| lesen)\s*$",
    ]
    out_lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            out_lines.append("")
            continue
        if len(s) <= 2:
            continue
        if any(re.search(p, s, flags=re.I) for p in noise):
            continue
        out_lines.append(ln)
    return "\n".join(out_lines).strip()

def _auto_scroll(page, max_steps: int = 30, step_delay_ms: int = 400):
    same_count = 0
    for _ in range(max_steps):
        height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(step_delay_ms)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == height:
            same_count += 1
        else:
            same_count = 0
        if same_count >= 2:
            break

def _expand_buttons(page):
    texts = ["Continue reading", "Read more", "Show more", "Mehr lesen", "Continue"]
    for t in texts:
        try:
            loc = page.get_by_text(t, exact=False)
            if loc and loc.count() > 0:
                for i in range(min(loc.count(), 3)):
                    try:
                        loc.nth(i).click(timeout=1000)
                        page.wait_for_timeout(500)
                    except Exception:
                        pass
        except Exception:
            pass

def _challenge_detected(page_text: str) -> bool:
    s = page_text.lower()
    return ("verify you are human" in s) or ("needs to review the security of your connection" in s)

@dataclass
class FetchResult:
    length: int
    saved_to: Optional[str]
    preview: str

def fetch_with_playwright(
    url: str,
    selector: str = DEFAULT_SELECTOR,
    headed: bool = False,
    storage_in: Optional[str] = None,
    storage_out: Optional[str] = None,
    user_agent: Optional[str] = None,
    timeout_ms: int = 30000,
    nav_timeout_ms: int = 30000,
    no_follow_external: bool = False,
    debug: bool = False,
    headed_on_challenge: bool = False,
    screenshot: Optional[str] = None,
    html_dump: Optional[str] = None,
) -> str:
    cookie_header = os.getenv("MEDIUM_COOKIE", "").strip()
    locale = os.getenv("PLAYWRIGHT_LOCALE", "en-US")
    timezone = os.getenv("PLAYWRIGHT_TZ", "Europe/Berlin")
    ua = user_agent or DESKTOP_CHROME_UA

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-gpu",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, args=launch_args)
        context_kwargs = {
            "locale": locale,
            "timezone_id": timezone,
            "user_agent": ua,
            "viewport": {"width": 1366, "height": 768},
            "device_scale_factor": 1.0,
        }
        if storage_in and os.path.exists(storage_in):
            context_kwargs["storage_state"] = storage_in
            if debug:
                print(f"[debug] loaded storage_state from {storage_in}", file=sys.stderr)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(nav_timeout_ms)

        # Mask webdriver
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        # Cookies setzen wenn kein storage_state
        if cookie_header and not storage_in:
            page.goto("https://medium.com/", wait_until="domcontentloaded")
            for name, value in _parse_cookie_header(cookie_header):
                js = f'document.cookie = "{name}={value}; path=/; domain=.medium.com; SameSite=Lax";'
                page.evaluate(js)

        # Ziel-URL
        page.goto(url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass

        # Challenge check
        body_text = page.evaluate("document.body.innerText || document.body.textContent || ''")
        if _challenge_detected(body_text):
            if debug:
                print("[debug] challenge detected", file=sys.stderr)
            if not headed and headed_on_challenge:
                # Relaunch headed and reuse current storage
                if debug:
                    print("[debug] reopening headed to solve challenge…", file=sys.stderr)
                # Save current state to temp
                tmp_state = storage_out or "tmp_medium_state.json"
                try:
                    context.storage_state(path=tmp_state)
                except Exception:
                    pass
                browser.close()
                browser = p.chromium.launch(headless=False, args=launch_args)
                context = browser.new_context(locale=locale, timezone_id=timezone, user_agent=ua, viewport={"width":1366,"height":768}, device_scale_factor=1.0)
                if os.path.exists(tmp_state):
                    context = browser.new_context(storage_state=tmp_state, locale=locale, timezone_id=timezone, user_agent=ua, viewport={"width":1366,"height":768}, device_scale_factor=1.0)
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                page.set_default_navigation_timeout(nav_timeout_ms)
                page.goto(url, wait_until="domcontentloaded")
                print("Bitte ggf. Challenge im sichtbaren Fenster lösen…", file=sys.stderr)
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    pass

        # Scroll/Expand
        _auto_scroll(page)
        _expand_buttons(page)

        # Inhalt holen
        text = ""
        try:
            if selector:
                el = page.locator(selector).first
                if el and el.count() > 0:
                    text = el.inner_text(timeout=timeout_ms)
        except Exception:
            pass

        if not text or len(text) < 2000:
            try:
                el = page.locator("article").first
                if el and el.count() > 0:
                    t2 = el.inner_text(timeout=timeout_ms)
                    if len(t2) > len(text):
                        text = t2
            except Exception:
                pass

        if not text or len(text) < 2000:
            try:
                sections = page.locator("section")
                count = sections.count()
                best = ""
                for i in range(min(count, 150)):
                    t = sections.nth(i).inner_text(timeout=timeout_ms)
                    if len(t) > len(best):
                        best = t
                if len(best) > len(text):
                    text = best
            except Exception:
                pass

        if not text or len(text) < 2000:
            try:
                text = page.evaluate("document.body.innerText || document.body.textContent || ''")
            except Exception:
                pass

        # Debug artifacts
        if screenshot:
            try:
                page.screenshot(path=screenshot, full_page=True)
                if debug:
                    print(f"[debug] saved screenshot -> {screenshot}", file=sys.stderr)
            except Exception as e:
                if debug:
                    print(f"[debug] screenshot failed: {e}", file=sys.stderr)
        if html_dump:
            try:
                html = page.content()
                with open(html_dump, "w", encoding="utf-8") as f:
                    f.write(html)
                if debug:
                    print(f"[debug] saved html -> {html_dump}", file=sys.stderr)
            except Exception as e:
                if debug:
                    print(f"[debug] html dump failed: {e}", file=sys.stderr)

        # Save state
        if storage_out:
            try:
                context.storage_state(path=storage_out)
                if debug:
                    print(f"[debug] saved storage_state -> {storage_out}", file=sys.stderr)
            except Exception as e:
                if debug:
                    print(f"[debug] save storage_state failed: {e}", file=sys.stderr)

        browser.close()

    return _clean_text(text or "")

def _parse_args():
    ap = argparse.ArgumentParser(description="Playwright-Renderer (headless-hardening, debug, auto-head on challenge)")
    ap.add_argument("--url", required=True, help="Ziel-URL")
    ap.add_argument("--out", default="", help="Ausgabedatei (z. B. article.txt)")
    ap.add_argument("--selector", default=DEFAULT_SELECTOR, help="CSS-Selector (default .meteredContent)")
    ap.add_argument("--headed", action="store_true", help="Chromium mit UI anzeigen (manuelle Schritte möglich)")
    ap.add_argument("--save-state", default="", help="Speichere Storage-State (Cookies) in Datei")
    ap.add_argument("--load-state", default="", help="Lade Storage-State (Cookies) aus Datei")
    ap.add_argument("--user-agent", default="", help="User-Agent überschreiben (default Desktop Chrome)")
    ap.add_argument("--timeout-ms", type=int, default=int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000")))
    ap.add_argument("--nav-timeout-ms", type=int, default=int(os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "30000")))
    ap.add_argument("--no-follow-external", action="store_true", help="Reserved (not used in v2.2)")
    ap.add_argument("--debug", action="store_true", help="Debug-Logs aktivieren")
    ap.add_argument("--headed-on-challenge", action="store_true", help="Bei Challenge automatisch headed neu öffnen")
    ap.add_argument("--screenshot", default="", help="Pfad für Screenshot (Debug)")
    ap.add_argument("--html-dump", default="", help="Pfad für HTML-Dump (Debug)")
    ap.add_argument("--print", action="store_true", help="Auszug (Preview) auf STDOUT ausgeben")
    return ap.parse_args()

def main():
    args = _parse_args()
    try:
        text = fetch_with_playwright(
            url=args.url,
            selector=args.selector,
            headed=args.headed,
            storage_in=(args.load_state or None),
            storage_out=(args.save_state or None),
            user_agent=(args.user_agent or None),
            timeout_ms=args.timeout_ms,
            nav_timeout_ms=args.nav_timeout_ms,
            no_follow_external=args.no_follow_external,
            debug=args.debug,
            headed_on_challenge=args.headed_on_challenge,
            screenshot=(args.screenshot or None),
            html_dump=(args.html_dump or None),
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    saved_to = None
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        saved_to = args.out

    preview = text[:900] + ("…" if len(text) > 900 else "")
    print("{")
    print(f' "length": {len(text)},')
    print(f' "saved_to": "{saved_to or ""}",')
    safe_preview = preview.replace('"', '\\"')
    print(f' "preview": "{safe_preview}"')
    print("}")

if __name__ == "__main__":
    main()
