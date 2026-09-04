"""
uber_session.py

This file manages a "persistent" Playwright browser session for Uber.

Why this file exists:
    We need to send authenticated requests to Uber's internal API (the
    same thing basescraper.py does), but a cookie you copy-paste once
    goes stale after a few weeks. Instead, we let a real Chromium browser
    stay logged in on disk (like your normal Chrome profile does), and
    we just ask it "what are my current cookies?" every time we need
    them. That way the session can refresh itself the way it would for
    a normal human using the site.

Two functions live here:
    1. login()             -- run this ONCE, by hand, to log in.
    2. get_fresh_cookies()  -- run this every time the scraper needs
                               fresh, valid cookies (fully automatic,
                               no human involved).
"""

from playwright.sync_api import sync_playwright
# `sync_playwright` is the "normal" (non-async) way to drive a browser
# with Playwright. Using this instead of the async API keeps the code
# looking like ordinary top-to-bottom Python, which is easier to read
# and debug than `async def` / `await` everywhere.

# This is the folder on your hard drive where the browser will save its
# profile: cookies, local storage, login state -- everything that makes
# it "remember" that you're logged in. Playwright creates this folder
# automatically the first time you use it; nothing to set up by hand.
PROFILE_DIR = "uber_profile"

# The Uber page we navigate to. Loading this page is what lets Uber's
# own frontend JavaScript refresh/renew short-lived session tokens --
# the same thing that happens invisibly every time you open a normal
# browser tab to a site you're already logged into.
UBER_URL = "https://m.uber.com"


def login():
    """
    Run this function ONCE, manually, whenever you need to (re-)log in.

    It opens a REAL, VISIBLE browser window so you can see the login
    page and type in your phone number / OTP / password yourself --
    Playwright does not (and should not) automate typing in your own
    login credentials. All this function does is:
      1. Open the browser with the persistent profile folder.
      2. Navigate to Uber.
      3. Wait for YOU to finish logging in.
      4. Save everything to disk when you're done, then close.
    """

    # `sync_playwright()` starts up the Playwright engine. We use a
    # `with` block so Playwright automatically cleans up (closes
    # connections, etc.) even if something goes wrong inside.
    with sync_playwright() as p:

        # `launch_persistent_context` is the key call in this whole
        # design. Unlike a normal `p.chromium.launch()` (which starts
        # a blank, throwaway browser with no memory), this points
        # Chromium at a specific folder (`user_data_dir=PROFILE_DIR`)
        # and tells it to save/load its profile there -- cookies,
        # login state, everything -- just like a real Chrome profile
        # folder on your computer.
        #
        # `headless=False` means "show me the actual browser window."
        # We want that here because a human (you) needs to see the
        # page to log in.
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
        )

        # A "context" can have multiple tabs/pages open at once (like
        # a browser window can have multiple tabs). We only need one,
        # so we open a single new page/tab to work with.
        page = context.new_page()

        # This actually navigates that page to Uber's site, the same
        # as if you typed the URL into the address bar yourself.
        page.goto(UBER_URL)

        # --- THIS IS THE MANUAL STEP ---
        # The browser window is now open and showing Uber's site. Go
        # to that window, log in exactly like you normally would
        # (phone number, OTP, whatever Uber asks for).
        #
        # `input(...)` pauses the Python script and waits for you to
        # press Enter in the TERMINAL (not the browser) -- this gives
        # you as much time as you need to finish logging in in the
        # browser window before the script continues.
        input("Log in to Uber in the browser window that just opened. "
              "Once you're fully logged in, come back here and press Enter...")

        # Once you've pressed Enter, we close the context. Closing it
        # is what actually flushes/saves the profile data (cookies,
        # session tokens) to the PROFILE_DIR folder on disk. From this
        # point on, that folder "remembers" that you're logged in.
        context.close()

    print("Login complete. Session saved to:", PROFILE_DIR)


def get_fresh_cookies():
    """
    Run this every time the scraper needs a valid, up-to-date set of
    cookies to make an authenticated request to Uber.

    Unlike login(), this needs ZERO human interaction -- it's meant to
    be called automatically, e.g. every few hours by a scheduled task.
    It reuses the SAME profile folder that login() created, so it's
    already logged in; it just needs to load the page briefly (which
    lets Uber's frontend refresh any short-lived tokens) and then read
    back whatever cookies are currently valid.

    Returns:
        A plain dict like {"sid": "...", "jwt-session": "...", ...} --
        exactly the shape the `requests` library wants for its
        `cookies=` argument.
    """

    with sync_playwright() as p:

        # Same persistent profile folder as login() -- this is what
        # makes it already authenticated. The only difference from
        # login() is `headless=True`: we don't want a visible window
        # popping up every few hours when nobody's watching.
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
        )

        page = context.new_page()

        # Loading the real page (rather than just reading cookies off
        # the profile folder directly) is intentional: it gives Uber's
        # own JavaScript a chance to run and refresh any token that's
        # close to expiring, the same as it would for a real visit.
        page.goto(UBER_URL)

        # `context.cookies()` returns a LIST of cookie objects, where
        # each one looks like:
        #   {"name": "sid", "value": "abc123...", "domain": "...", ...}
        # We only care about the name and value for making our own
        # `requests` call later, so we build a simple dict out of it.
        raw_cookies = context.cookies()

        cookie_dict = {}
        for cookie in raw_cookies:
            cookie_dict[cookie["name"]] = cookie["value"]

        # Always close the context when you're done with it -- this
        # releases the browser process and, just like in login(),
        # saves anything that changed back to the profile folder
        # (e.g. a freshly-refreshed token) so next time is up to date.
        context.close()

    return cookie_dict


# This block only runs if you execute `python uber_session.py` directly
# (not when this file gets imported by another script, like
# auto_logger.py will do later). It's a quick manual way to test each
# function on its own before wiring them into the rest of the pipeline.
if __name__ == "__main__":
    # Run login() FIRST, by itself, the very first time. Then comment
    # it back out and try get_fresh_cookies() instead, to confirm the
    # saved session actually works headlessly.

    #login()

    cookies = get_fresh_cookies()
    print("Got", len(cookies), "cookies")
