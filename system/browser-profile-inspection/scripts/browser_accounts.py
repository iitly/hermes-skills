#!/usr/bin/env python
"""列出本机 Chromium 系浏览器各配置里登录的账号。

只读 Local State / Preferences / Secure Preferences 三个 JSON，
不碰 cookie、不需要浏览器关闭、不联网。

用法：python browser_accounts.py [--json]
"""
import json
import os
import sys

BROWSERS = {
    "Chrome": r"%LOCALAPPDATA%\Google\Chrome\User Data",
    "Edge": r"%LOCALAPPDATA%\Microsoft\Edge\User Data",
    "Brave": r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data",
    "Chromium": r"%LOCALAPPDATA%\Chromium\User Data",
}


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def signin_time(pref):
    try:
        return (
            pref["google"]["services"]["signin"]["REFRESH_TOKEN_RECEIVED"]["time"]
        )
    except (KeyError, TypeError):
        return None


def accounts_for(prof_dir):
    pref = load_json(os.path.join(prof_dir, "Preferences")) or {}
    rows = []
    for a in pref.get("account_info") or []:
        rows.append(
            {
                "email": a.get("email"),
                "name": a.get("full_name"),
                "gaia": a.get("gaia") or a.get("account_id"),
                "locale": a.get("locale"),
                "token_at": signin_time(pref),
            }
        )
    if not rows:
        sec = load_json(os.path.join(prof_dir, "Secure Preferences")) or {}
        try:
            last = sec["google"]["services"]["last_signed_in_username"]
        except (KeyError, TypeError):
            last = None
        if last:
            rows.append(
                {
                    "email": last,
                    "name": None,
                    "gaia": None,
                    "locale": None,
                    "token_at": signin_time(pref),
                }
            )
    return rows


def scan():
    out = []
    for browser, raw in BROWSERS.items():
        root = os.path.expandvars(raw)
        if not os.path.isdir(root):
            continue
        state = load_json(os.path.join(root, "Local State")) or {}
        info = (state.get("profile") or {}).get("info_cache") or {}
        browser_country = state.get("variations_country")
        if not info:
            info = {"Default": {}}
        for prof in info:
            prof_dir = os.path.join(root, prof)
            if not os.path.isdir(prof_dir):
                continue
            rows = accounts_for(prof_dir)
            if not rows:
                rows = [{"email": None, "name": None, "gaia": None, "locale": None, "token_at": None}]
            for r in rows:
                r.update(
                    {
                        "browser": browser,
                        "profile": prof,
                        "profile_name": (info.get(prof) or {}).get("name"),
                        "browser_country": browser_country,
                    }
                )
                out.append(r)
    return out


def main():
    rows = scan()
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("未发现 Chromium 系浏览器的用户数据目录。")
        return
    for r in rows:
        label = f"{r['browser']}/{r['profile']}" + (
            f" ({r['profile_name']})" if r.get("profile_name") else ""
        )
        print(f"[{label}]")
        print(f"  email      : {r['email'] or '（未登录）'}")
        print(f"  name/gaia  : {r['name'] or '-'} / {r['gaia'] or '-'}")
        print(f"  locale     : {r['locale'] or '-'}")
        print(f"  refresh tok: {r['token_at'] or '-'}")
        print(f"  浏览器地区 : {r['browser_country'] or '-'}  (仅浏览器，非账号地区)")


if __name__ == "__main__":
    main()
