# IFC Researcher Scraper

A web scraper that builds a structured dataset of the researchers at the
[Instituto de Fisiología Celular (IFC), UNAM](https://www.ifc.unam.mx/). It
collects each researcher's department, research interests, lines of research,
academic background, career history and contact e-mail.

The project was purely as an academic project. The scraper is the data-collection stage: it turns the IFC's
researcher pages, which are written for people to browse, into JSON that later
analysis and modelling can use.



## Why

The IFC lists its researchers in several departments, and each researcher has
their own profile page. To compare research areas or find a lab working on a
topic, you have to open every page by hand. This project:

1. Collects all of those pages automatically and politely (it obeys
   `robots.txt`, sends one request at a time and waits 1 s between requests).
2. Stores them in one consistent JSON file.
3. Produces a text corpus of research descriptions that NLP and ML methods
   can use (topic modelling, embeddings, similarity search, clustering).

## How it works

```
investigacion.php ──► department pages ──► researcher profile pages
   (6 departments)     (researcher links)     (info text + e-mail)
```

The site renders its content with JavaScript, so requests go through a
headless Chromium browser via
[scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright).
See [docs/architecture.md](docs/architecture.md) for details.

The last run collected **6 departments** and **59 researchers**, with profile
text and an e-mail for all 59.

## Quick start

### 1. Create the environment

With conda:

```bash
conda env create -f environment.yml
conda activate ifc-grab
playwright install chromium
```

Or with pip:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the spider

```bash
cd ifc_grab
scrapy crawl ifc_v4
```

The results are written to `data/` at the repository root, whichever
directory you run the command from:

| File | Contents |
|---|---|
| `data/output.json` | List of departments with their researchers |

The format is documented in [docs/data-format.md](docs/data-format.md).

### Configuration

Nothing is hardcoded to a particular machine. You can override the defaults:

| Setting | Default | Override |
|---|---|---|
| Output directory | `<repo>/data` | `IFC_OUTPUT_DIR=/path` env var, or `-s OUTPUT_DIR=/path` |
| Start URL | `https://www.ifc.unam.mx/investigacion.php` | `IFC_START_URL=...` env var, or `-a start_url=...` |

Example:

```bash
scrapy crawl ifc_v4 -s OUTPUT_DIR=../runs/2026-10-19
```

## Repository layout

```
.
├── README.md                  ← you are here
├── environment.yml            conda environment
├── requirements.txt           pip dependencies
├── .github/workflows/ci.yml   CI: install and check the spider loads
├── data/                      scraper output (not committed)
├── docs/
│   ├── architecture.md        crawl flow and code walkthrough
│   └── data-format.md         JSON schema of the output
└── ifc_grab/                  Scrapy project
    ├── scrapy.cfg
    └── ifc_grab/
        ├── settings.py        crawl settings, output path, start URL
        ├── pipelines.py       writes output.json
        ├── items.py           (Scrapy boilerplate, unused)
        ├── middlewares.py     (Scrapy boilerplate, unused)
        └── spiders/
            └── ifc_v4.py      the spider
```

## Data and ethics

The output contains personal information (names and institutional e-mail
addresses). The information is public on the IFC website, but the scraped
files are **excluded from the repository by `.gitignore`** so that the
repository does not republish a harvestable e-mail list. Regenerate the data
locally by running the spider. Use it for academic purposes only, and keep the
polite crawl settings (`ROBOTSTXT_OBEY`, `DOWNLOAD_DELAY`,
`CONCURRENT_REQUESTS = 1`).

## Continuous integration

On every push to `main` and on every pull request, GitHub Actions installs the
dependencies, compiles the sources and checks that the `ifc_v4` spider is
registered. CI does **not** crawl the live site.

## Author

[@m0ss6](https://github.com/m0ss6)
