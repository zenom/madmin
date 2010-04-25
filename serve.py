from __future__ import with_statement

import ConfigParser
import os
import pymongo

from flask import flash, Flask, g, render_template, request, session, redirect,\
    url_for, abort

app = Flask(__name__)
config = ConfigParser.ConfigParser()
config.readfp(open("madmin.ini"))

###############################
## Before Request
###############################

@app.before_request
def connect_mongo():
    servers = {}
    sections = config.sections()
    for section in sections:
        if "server" in section:
            host = config.get(section, "host", "127.0.0.1")
            port = config.getint(section, "port")
            name = config.get(section, "name", None)
            server_info = dict(name=name, host=host, port=port)
            servers.update({section: server_info})
    
    ## if nothing was configured, setup the basic defaults
    if not servers:
        server = dict(name="Default", host="127.0.0.1", port=27017)
        servers.update({"server_1": server})
        
    ## If the default option is not set choose the first one.
    if not config.has_option("madmin", "default"):
        first = servers.keys()[0]
        server = servers.get(first)
    else:
        default = config.get("madmin", "default")
        server = servers.get(default)
    
    ## connect up to the initial mongo server.
    try:
        g.mongo = pymongo.Connection(server.get("host"), server.get("port"))
    except pymongo.errors.ConnectionFailure, e:
        return "Unable to connect to MongoDB instance."
         

##############################
# Database Management
##############################
@app.route("/")
def databases():
    
    databases = []
    
    for database in g.mongo.database_names():
        total_indexes = 0
        total_size = 0
        total_index_size = 0
        
        # don't want people removing these as I believe they are important
        if database in ["test", "local"]:
                continue

        for coll in g.mongo[database].collection_names():
            
            try:
                idx_info = g.mongo[database].command("collstats", coll, safe=True)
            except pymongo.OperationalError, e:
                print e
                
            total_indexes += idx_info.get("nindexes")
            total_size += idx_info.get("storageSize") 
            total_index_size += idx_info.get("totalIndexSize")
        
        db = dict(
            name=database, 
            size=total_size, 
            indexes=total_indexes, 
            collections=len(g.mongo[database].collection_names()),
            index_size=total_index_size,
        )
        databases.append(db)
    
    return render_template("index.html", databases=databases)
    
    
@app.route("/database/clone", methods=["POST",])
def clone_database():
    if request.method == "POST":
        if "from" in request.form and "to" in request.form:
            from_db = request.form.get("from")
            to_db = request.form.get("to")
            
            try:
                g.mongo.copy_database(from_db, to_db)
                flash("%s has been cloned to %s." % (from_db, to_db))
            except pymongo.errors.InvalidName:
                return "Originating database does not exist."
            except TypeError:
                return "From & To must be strings."
            except pymongo.errors.OperationError, e:
                print e
                return "Unable to clone database."
            finally:
                return ""
            
    
@app.route("/database/repair/<database>")
def repair_database(database):
    try:
        g.mongo[database].command("repairDatabase", safe=True)
    except pymongo.errors.OperationError, e:
        return "Unable to repair database."
        
    flash("%s has been repaired." % (database))
    return redirect(url_for("databases"))

    
@app.route("/database/drop/<database>")
def drop_database(database):
    try:
        g.mongo.drop_database(database)
        flash("%s has been dropped." % database)
    except Exception ,e:
        flash("Unable to drop %s. (%s)" % (database, e))
        
    return redirect(url_for("databases"))
        
        
##############################
# Collection Management
##############################

@app.route("/<database>/collections")
def list_collections(database):
    
    collections = []
    for coll in g.mongo[database].collection_names():
        if coll in ["system.indexes",]:
            continue
            
        total_indexes = total_size = total_index_size = 0
        try:
            idx_info = g.mongo[database].command("collstats", coll, safe=True)
        except pymongo.OperationalError, e:
            print e
            
        total_indexes += idx_info.get("nindexes")
        total_size += idx_info.get("storageSize") 
        total_index_size += idx_info.get("totalIndexSize")
    
        collection = dict(
            name=coll, 
            size=total_size, 
            indexes=total_indexes, 
            index_size=total_index_size,
            documents=idx_info.get("count")
        )
        collections.append(collection)
    return render_template("collections.html", collections=collections)
        
        
##############################
# Filters
##############################
def pretty_size(size):
    kb = float(size) / float(1024)
    mb = kb / float(1024)
    gb = mb / float(1024)
    
    if gb > 1:
        return "%s GB" % (round(gb, 2))
    
    if mb > 1:
        return "%s MB" % (round(mb,2))
        
    return "%s KB" % (round(kb,2))
    
app.jinja_env.filters["pretty_size"] = pretty_size

if __name__ == "__main__":
    app.secret_key = "kTNpaQRVgJzwwTxcavixEpQqTwQezSVJLkALaUiJDj0fBc1Cfd"
    app.run(host=config.get("madmin", "host"), port=int(config.getint("madmin", "port")), debug=True)