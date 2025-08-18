# playlistwatcher

Playlistwatcher is a Django web application developed to allow you to track Spotify playlists containing your tracks, with storage in a database, web interface, import/export to Excel and scheduled tasks.

## Running Locally

```bash
git clone https://github.com/fmoreau69/playlistwatcher.git
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py runserver
```