"""Drive Gearbox headless against local fixtures. Usage: drive.py BASE_URL OUTDIR [query...]"""
import sys, json, os, asyncio
from playwright.async_api import async_playwright

LIB = "/home/claude/work/lib"
ROUTES = {
    "proj4@2.12.1/dist/proj4.js": LIB + "/proj4-2.12.1/package/dist/proj4.js",
    "geotiff@2.1.3/dist-browser/geotiff.js": LIB + "/geotiff-2.1.3/package/dist-browser/geotiff.js",
    "fzstd@0.1.1/umd/index.js": LIB + "/fzstd/package/umd/index.js",
    "zarrita@0.7.5/+esm": "/home/claude/work/zb/zarrita-bundle.mjs",
}

async def main(base, outdir, queries, dpr):
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as p:
        kw = {}
        if os.environ.get("PROXY"):
            kw["proxy"] = {"server": os.environ["PROXY"], "bypass": "127.0.0.1,localhost"}
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", **kw)
        ctx = await b.new_context(viewport={"width": 1400, "height": 900}, device_scale_factor=dpr)
        async def route(r):
            u = r.request.url
            for k, v in ROUTES.items():
                if k in u:
                    return await r.fulfill(path=v, content_type="application/javascript", headers={"Access-Control-Allow-Origin": "*"})
            if os.environ.get("PROXY") and u.startswith("http://127.0.0.1:8765/index.html"):
                return await r.fulfill(path="/tmp/claude-0/site/index.html", content_type="text/html")
            if "fonts.g" in u:
                return await r.fulfill(status=200, body="", content_type="text/css")
            return await r.continue_()
        await ctx.route("**/*", route)
        for qi, q in enumerate(queries):
            page = await ctx.new_page()
            errs = []
            page.on("console", lambda m: errs.append(m.type + ": " + m.text) if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
            await page.goto(base + "?" + q)
            try:
                await page.wait_for_function("window.GEARBOX && window.GEARBOX.logRows.length > 0", timeout=60000)
            except Exception as e:
                errs.append("timeout waiting for a settled view")
            await page.wait_for_timeout(500)
            # zoom out, then in, letting each view settle
            for step, f in enumerate([4, 1/16, 1/4]):
                n0 = await page.evaluate("window.GEARBOX.logRows.length")
                await page.evaluate("(() => { const G = window.GEARBOX; G.VIEW.res *= %r; G.viewChanged(); })()" % f)
                try:
                    await page.wait_for_function("window.GEARBOX.logRows.length > %d" % n0, timeout=60000)
                except Exception:
                    errs.append("timeout after zoom %d" % step)
                await page.wait_for_timeout(300)
            rows = await page.evaluate("JSON.stringify(window.GEARBOX.logRows)")
            huds = await page.evaluate("[...document.querySelectorAll('.hud')].map(h => h.innerText)")
            await page.screenshot(path=os.path.join(outdir, "shot_%d.png" % qi))
            print("==", q)
            for r in json.loads(rows)[::-1]:
                print(" view", r["id"], r["label"])
                for pp in r["panels"]:
                    print("   ", pp["name"], "|", pp["levels"], "| files", pp["files"], "req", pp["req"], "bytes", pp["bytes"], "calls", pp["calls"], "refused" if pp["refused"] else "")
            print(" huds:", [h.replace("\n", " / ") for h in huds])
            for e in errs[:12]:
                print(" ERR", e)
            await page.close()
        await b.close()

base, outdir = sys.argv[1], sys.argv[2]
dpr = float(os.environ.get("DPR", "1"))
asyncio.run(main(base, outdir, sys.argv[3:], dpr))
