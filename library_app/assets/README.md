# Label assets

Place the library bookplate logo here as:

    label_logo.png

It is used as a soft background watermark on every printed book label
(see `library_app/services/label_service.py`). A PNG with a transparent
background looks best, but a white-background PNG works too (white blends
into the label).

Notes:
- If this file is absent, labels still render fine — just without the
  watermark (graceful fallback).
- To use a logo from a different location, set the environment variable
  `LIBRARY_LABEL_LOGO=/full/path/to/logo.png`.
- The build scripts (`build.sh` / `build.bat`) bundle this folder into the
  packaged app, so the logo ships inside the `.app` / `.exe`.
