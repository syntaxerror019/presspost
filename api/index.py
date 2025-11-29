from flask import Flask, render_template, request, redirect, url_for
import redis
import os
import hashlib
import base64
import json
import datetime
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
r = redis.from_url(os.getenv("DB_URL"), db=1, decode_responses=True)

@app.route('/')
def home():
    all_blogs = []
    for key in r.scan_iter("posts:*"):
        blog_name = key.split("posts:")[1]
        all_blogs.append(blog_name)
    return render_template('index.html', all_blogs=all_blogs)

@app.route('/signup')
def signup():
    name = request.args.get('name').replace(" ", "_")
    password = request.args.get('password', None)
    if name and password:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        r.hset(f"user:{name}", mapping={"password": hashed_password})
        return redirect(url_for('blog', name=name))
    return render_template('signup.html', name=name.replace("_", " "))

@app.route('/blog/<name>', methods=['GET', 'POST'])
def blog(name):
    name = unquote(name).replace(" ", "_")
    raw_posts = r.lrange(f"posts:{name}", 0, -1)  # all posts
    
    if not r.exists(f"user:{name}"):
        return redirect(url_for('home'))
    
    posts = []
    for post in raw_posts:
        post_data = json.loads(post)
        posts.append(post_data)
    
    return render_template('blog.html', name=name.replace("_", " "), posts=posts)

@app.route('/blog/<name>/new', methods=['POST', 'GET'])
def new_post(name):
    name = unquote(name).replace(" ", "_")
    auth = request.form.get('auth', None)
    if auth is None:
        return render_template('auth.html', name=name.replace("_", " ")), 200

    stored_password = r.hget(f"user:{name}", "password")
    if stored_password != hashlib.sha256(auth.encode()).hexdigest():
        return render_template('auth.html', name=name.replace("_", " "), error="Wrong Password"), 401

    title = request.form.get('title', None)
    content = request.form.get('content', None)
    
    if not title or not content:
        return render_template('new_post.html', name=name.replace("_", " "), pw=auth)

    # Handle multiple images
    images_base64 = []
    for image_file in request.files.getlist('images'):
        if image_file and image_file.filename != '':
            images_base64.append(base64.b64encode(image_file.read()).decode('utf-8'))

    # Save the post in Redis
    post_data = {
        "title": title,
        "content": content,
        "images": images_base64,
        "date": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }

    r.lpush(f"posts:{name}", json.dumps(post_data))

    return redirect(f"/blog/{name}")

@app.route('/blog/<name>/post/<int:post_id>', methods=['GET'])
def post(name, post_id):
    name = unquote(name).replace(" ", "_")
    raw_posts = r.lrange(f"posts:{name}", 0, -1)  # all posts
    
    if not raw_posts or post_id < 0 or post_id >= len(raw_posts):
        return "Post not found", 404
    
    post_data = json.loads(raw_posts[post_id])
    
    return render_template('post.html', name=name.replace("_", " "), post=post_data, post_id=post_id)

@app.route('/blog/<name>/post/<int:post_id>/delete', methods=['GET', 'POST'])
def delete_post(name, post_id):
    name = unquote(name).replace(" ", "_")
    auth = request.form.get('auth', None)
    if auth is None:
        return render_template('auth.html', name=name.replace("_", " ")), 200

    stored_password = r.hget(f"user:{name}", "password")
    if stored_password != hashlib.sha256(auth.encode()).hexdigest():
        return render_template('auth.html', name=name.replace("_", " "), error="Wrong Password"), 401

    raw_posts = r.lrange(f"posts:{name}", 0, -1)
    
    if not raw_posts or post_id < 0 or post_id >= len(raw_posts):
        return "Post not found", 404

    # Remove the post
    r.lrem(f"posts:{name}", 1, raw_posts[post_id])

    return redirect(f"/blog/{name}")

@app.route('/blog/<name>/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(name, post_id):
    name = unquote(name).replace(" ", "_")
    auth = request.form.get('auth', None)
    if auth is None:
        return render_template('auth.html', name=name.replace("_", " ")), 200

    stored_password = r.hget(f"user:{name}", "password")
    if stored_password != hashlib.sha256(auth.encode()).hexdigest():
        return render_template('auth.html', name=name.replace("_", " "), error="Wrong Password"), 401

    raw_posts = r.lrange(f"posts:{name}", 0, -1)
    
    if not raw_posts or post_id < 0 or post_id >= len(raw_posts):
        return "Post not found", 404

    if request.method == 'POST':
        title = request.form.get('title', None)
        content = request.form.get('content', None)
        
        if not title or not content:
            return render_template('edit_post.html', name=name.replace("_", " "), post=json.loads(raw_posts[post_id]), pw=auth)

        # Handle multiple images
        images_base64 = json.loads(raw_posts[post_id]).get('images', [])
        for image_file in request.files.getlist('images'):
            if image_file and image_file.filename != '':
                images_base64.append(base64.b64encode(image_file.read()).decode('utf-8'))

        # Update the post in Redis
        post_data = {
            "title": title,
            "content": content,
            "images": images_base64,  # list of Base64 images
            "date": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        }

        r.lset(f"posts:{name}", post_id, json.dumps(post_data))

        return redirect(f"/blog/{name}/post/{post_id}")

    post_data = json.loads(raw_posts[post_id])
    return render_template('edit_post.html', name=name.replace("_", " "), post=post_data)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', error=e), 500

if __name__ == '__main__':
    app.run(debug=True)