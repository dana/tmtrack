#!/usr/bin/env python3
"""
dev-browser.py: Headless Chrome CDP automation tool for TMTrack dev stack.
Enables autonomous screenshot capture, session login, DOM inspection, and JS evaluation.
"""
import argparse
import asyncio
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import websockets

CDP_PORT = int(os.environ.get("DEV_CHROME_PORT", 9223))
CDP_BASE = f"http://127.0.0.1:{CDP_PORT}"


def get_tab():
    try:
        with urllib.request.urlopen(f"{CDP_BASE}/json/list", timeout=3) as resp:
            tabs = json.loads(resp.read().decode())
            for t in tabs:
                if t.get("type") == "page":
                    return t
        with urllib.request.urlopen(f"{CDP_BASE}/json/new?http://127.0.0.1:8080/", timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Error connecting to Chrome CDP on {CDP_BASE}: {e}", file=sys.stderr)
        print("Is dev stack running? (Run './dev-stack.sh up' first)", file=sys.stderr)
        sys.exit(1)


async def send_cmd(ws, method, params=None, msg_id=1):
    req = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            return msg


async def take_screenshot(url, output_path, delay=1.0, user=None):
    tab = get_tab()
    target_url = url or "http://127.0.0.1:8080/"
    async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=50*1024*1024) as ws:
        await send_cmd(ws, "Page.enable", msg_id=1)
        
        if user:
            encoded_next = urllib.parse.quote(target_url)
            login_url = f"http://127.0.0.1:5050/api/auth/dev-login?userid={user}&next={encoded_next}"
            await send_cmd(ws, "Page.navigate", {"url": login_url}, msg_id=2)
            await asyncio.sleep(delay + 0.5)
        else:
            await send_cmd(ws, "Page.navigate", {"url": target_url}, msg_id=3)
            await asyncio.sleep(delay)
        
        res = await send_cmd(ws, "Page.captureScreenshot", {"format": "png"}, msg_id=4)
        if "result" not in res or "data" not in res["result"]:
            print(f"Failed to capture screenshot: {res}", file=sys.stderr)
            sys.exit(1)
            
        img_bytes = base64.b64decode(res["result"]["data"])
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(img_bytes)
        print(f"Screenshot successfully saved to {abs_path} ({len(img_bytes)} bytes)")


async def evaluate_js(expr):
    tab = get_tab()
    async with websockets.connect(tab["webSocketDebuggerUrl"]) as ws:
        await send_cmd(ws, "Runtime.enable", msg_id=1)
        res = await send_cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True}, msg_id=2)
        val = res.get("result", {}).get("result", {}).get("value")
        print(json.dumps(val, indent=2))


async def click_element(selector, delay=0.5):
    tab = get_tab()
    async with websockets.connect(tab["webSocketDebuggerUrl"]) as ws:
        await send_cmd(ws, "Runtime.enable", msg_id=1)
        expr = f"""(function() {{
            const el = document.querySelector('{selector}');
            if (!el) return 'Element not found: ' + '{selector}';
            el.click();
            return 'Clicked ' + '{selector}';
        }})()"""
        res = await send_cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True}, msg_id=2)
        val = res.get("result", {}).get("result", {}).get("value")
        print(val)
        if delay > 0:
            await asyncio.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description="TMTrack Dev Browser Automation")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # screenshot
    p_snap = subparsers.add_parser("screenshot", help="Capture a screenshot")
    p_snap.add_argument("output", nargs="?", default="/tmp/tmtrack-dev-screenshot.png", help="Output PNG path")
    p_snap.add_argument("--url", default="http://127.0.0.1:8080/", help="URL to navigate to")
    p_snap.add_argument("--user", default=None, help="User to log in as (e.g. diederich@gmail.com)")
    p_snap.add_argument("--delay", type=float, default=1.0, help="Wait seconds before capture")

    # eval
    p_eval = subparsers.add_parser("eval", help="Evaluate JavaScript expression")
    p_eval.add_argument("expression", help="JavaScript code to evaluate")

    # click
    p_click = subparsers.add_parser("click", help="Click an element selector")
    p_click.add_argument("selector", help="CSS selector")
    p_click.add_argument("--delay", type=float, default=0.5, help="Wait seconds after click")

    args = parser.parse_args()

    if args.action == "screenshot":
        asyncio.run(take_screenshot(args.url, args.output, delay=args.delay, user=args.user))
    elif args.action == "eval":
        asyncio.run(evaluate_js(args.expression))
    elif args.action == "click":
        asyncio.run(click_element(args.selector, delay=args.delay))


if __name__ == "__main__":
    main()
