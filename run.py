from app import app, socketio
from app.controllers import register_user
import click

@app.cli.command("create-user")
@click.argument("username")
@click.argument("email")
@click.argument("password")
def create_user(username, email, password):
    # Allows for the creation of a new user from the command line
    # Use with `flask --app run create-user <username> <email> <password>`
    user, errors = register_user({
        'username': username,
        'email': email,
        'password': password
    })
    if errors:
        print(f"Error: {errors}")
    else:
        print(f"User created: {user.username} ({user.email})")

@app.cli.command("dump-photos")
def dump_photos_command():
    """Exports photo data from the database to photos.json"""
    from app.image_upload import sync_photos_to_json
    sync_photos_to_json()
    print("Photos exported to photos.json")

@app.cli.command("load-photos")
def load_photos_command():
    """Imports photo data from photos.json to the database"""
    from app.image_upload import load_photos_from_json
    added = load_photos_from_json()
    print(f"Loaded {added} new photos from photos.json into the database")

@app.cli.command("admin-promote")
@click.argument("username")
def admin_promote(username):
    """Promotes a user to admin from the command line"""
    from app.models import User
    from app import db
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"User {username} not found")
        return
    user.is_admin = True
    db.session.commit()
    print(f"{username} has been promoted to admin")

@app.cli.command("admin-demote")
@click.argument("username")
def admin_demote(username):
    """Demotes a user from admin from the command line"""
    from app.models import User
    from app import db
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"User {username} not found")
        return
    user.is_admin = False
    db.session.commit()
    print(f"{username} has been demoted from admin")

@app.cli.command("migrate-photos-to-r2")
def migrate_photos_to_r2():
    """Migrate all registered local photos to Cloudflare R2 bucket"""
    from app.models import Photos
    from app.config import Config
    import os
    
    if not Config.R2_ENABLED:
        print("R2 is not enabled (R2_ENABLED is false). Aborting migration.")
        return

    from app.r2_storage import upload_photo_bytes

    photos = Photos.query.all()
    print(f"Starting migration of {len(photos)} photos to Cloudflare R2...")

    success_count = 0
    skip_count = 0
    error_count = 0

    base_dir = os.path.dirname(os.path.abspath(__file__))

    for photo in photos:
        # Canonical key on R2
        key = photo.image_path.lstrip('/')
        local_path = os.path.join(base_dir, 'app', key)

        if not os.path.exists(local_path):
            print(f"SKIP: Local file not found for {photo.image_path} (expected path: {local_path})")
            skip_count += 1
            continue

        try:
            with open(local_path, 'rb') as f:
                data = f.read()
            upload_photo_bytes(data, key)
            print(f"OK: Uploaded {photo.image_path} to R2")
            success_count += 1
        except Exception as e:
            print(f"ERROR: Failed to upload {photo.image_path} to R2: {e}")
            error_count += 1

    print("\nMigration finished!")
    print(f"Successfully uploaded: {success_count}")
    print(f"Skipped (not found):  {skip_count}")
    print(f"Failed with error:    {error_count}")

if __name__ == "__main__":
    socketio.run(app, debug=True)