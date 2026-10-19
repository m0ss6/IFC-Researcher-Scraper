# Architecture

The scraper is a single [Scrapy](https://scrapy.org/) spider, `ifc_v4`
([ifc_grab/ifc_grab/spiders/ifc_v4.py](../ifc_grab/ifc_grab/spiders/ifc_v4.py)).
It crawls the IFC website three levels deep and keeps everything in memory
until the spider closes.

## Why Playwright

The IFC pages load their content with JavaScript, and some department pages
include embedded videos that delay rendering. A plain HTTP download returns
incomplete HTML. The spider therefore sends every request through
`scrapy-playwright`, which loads the page in headless Chromium and waits for
specific CSS selectors before Scrapy parses the result. This requires the
asyncio Twisted reactor, which the spider sets in its `custom_settings`.

## Crawl flow

### Level 1: `parse` (department index)

* **URL:** `IFC_START_URL` (default `https://www.ifc.unam.mx/investigacion.php`)
* **Waits for:** `div[class*="contenedor-con-bordes"]` and its `h2`/`p`/`a`
  children, then network idle.
* **Extracts:** for each container, the department title and link
  (`a.text-5`).
* **Stores:** one dict per department in `self.scraped_data`.
* **Next:** one request per department, sent to `second_parse`.

### Level 2: `second_parse` (department page)

* **Waits for:** `div.card-body7` and the `a` tags inside it, then scrolls
  500 px and waits 1 s so lazy-loaded cards appear.
* **Extracts:** from every `div[class*="card-body"]`, the researcher's name
  (link text) and profile URL.
* **Stores:** `department["Researchers"][name] = {"Researcher link": url}`.
* **Next:** one request per researcher, sent to `third_parse` with the
  department index and researcher name in `meta`.

### Level 3: `third_parse` (researcher profile)

* **Waits for:** `div.col-lg-12` and the e-mail paragraph, then network idle.
* **Profile text:** every non-empty text node inside `div.col-lg-12`. If that
  block is missing, the spider tries a list of fallback selectors
  (`.post-info-s`, `.fontz-15`, …).
* **E-mail:** read from the `p.post-info-s…fontz-15` paragraph. If that text
  is not an e-mail, the spider searches it, and then the whole page, with a
  regular expression.
* **Stores:** `researcher info` (list of strings) and `email` on the
  researcher's entry. If no text was found, it sets `extraction_failed: true`.
* **Errors:** `errback_third_parse` marks the entry with
  `request_failed: true` and the error message.

### Shutdown

When the crawl finishes:

1. `Ifc_v4.closed()` prints summary statistics (counts, e-mail and success
   rates) and writes `OUTPUT_DIR/output.json`.
2. `FinalOutputPipeline.close_spider()`
   ([pipelines.py](../ifc_grab/ifc_grab/pipelines.py)) writes
   `OUTPUT_DIR/output.json`.

The spider never yields Scrapy items. All data lives in the spider's
`whole_scrape` / `scraped_data` attributes and is written to disk at the end.
If the process is killed partway through, nothing is saved.

## Known quirks

* `second_parse` starts the level-3 requests for *every* department it has
  seen so far, not only its own. Scrapy's duplicate filter drops the repeated
  URLs, so the output is correct, but the log shows the summary block several
  times.
* The selectors are tied to the IFC site's current CSS classes. If the site is
  redesigned, the waits in `playwright_page_methods` will time out and the
  selectors will need updating.
* `items.py` and `middlewares.py` are unchanged `scrapy startproject`
  boilerplate.

## Settings that matter

From [settings.py](../ifc_grab/ifc_grab/settings.py) and the spider's
`custom_settings`:

| Setting | Value | Purpose |
|---|---|---|
| `ROBOTSTXT_OBEY` | `True` | Respect the site's crawl rules |
| `CONCURRENT_REQUESTS` | `1` | One page at a time |
| `DOWNLOAD_DELAY` | `1` | One-second pause between requests |
| `OUTPUT_DIR` | `<repo>/data` | Where JSON is written (`IFC_OUTPUT_DIR` env var) |
| `IFC_START_URL` | IFC research index | Entry point (`-a start_url=` also works) |
