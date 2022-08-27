from rethinkdb import RethinkDB

# RethinkDB settings
db_name = "blog_jirione"
r = RethinkDB()
rethinkdb_ip = "localhost"
rethinkdb_port = 28015
conn = r.connect(rethinkdb_ip, rethinkdb_port, db=db_name)
topics = r.table("topics")
posts = r.table("posts")
comments = r.table("comments")
authors = r.table("authors")
