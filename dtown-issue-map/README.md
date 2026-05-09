# Downtown Kingston Issue Map

A small map-first issue dashboard for Downtown Kingston with:

- KML-driven point loading
- status filtering on the public map
- an admin page for status updates and KML replacement
- a backend that works locally and on Vercel

## Project structure

```text
dtown-issue-map/
  public/
    index.html
    admin.html
    static/
      css/
        styles.css
      js/
        app.js
        admin.js
      images/
        our-city-kingston.png
        dkri-colour-logo.png
  data/
    issues.kml
    statuses.json
    archive/
  app.py
  issue_map_backend.py
  requirements.txt
  server.py
  vercel.json
```

## Install dependencies

```powershell
cd dtown-issue-map
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Run locally

```powershell
.\.venv\Scripts\python server.py
```

Then open:

- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/admin/`

## Live Server preview

If you want to use VS Code Live Server for the frontend preview:

1. open `public/index.html` or `public/admin.html`
2. keep `.\.venv\Scripts\python server.py` running in a terminal

The frontend automatically points API calls to `http://127.0.0.1:8080/api` during local Live Server previews, so CSS loads correctly from `public/static` and the map/admin screens still have backend access.

## Quick validation

```powershell
.\.venv\Scripts\python server.py --check
```

## Deploy on Vercel

This project is prepared for simple Vercel hosting using:

- `app.py` as the Flask entrypoint
- `public/` for HTML, CSS, JS, and images
- `vercel.json` for clean URLs and function bundling

When creating the Vercel project, set the **Root Directory** to:

```text
dtown-issue-map
```

Main routes after deploy:

- `/`
- `/admin`
- `/api/issues`
- `/api/statuses`
- `/api/kml`

## Replace the KML

Use the admin page and upload a new `.kml` file.

On upload:

1. the current KML is archived in `data/archive/`
2. the new file becomes `data/issues.kml`
3. the app re-syncs status entries
4. matching point IDs or names keep their old statuses where possible
