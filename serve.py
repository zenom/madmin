import pymongo

from flask import flash, Flask, g, render_template

app = Flask(__name__)

@app.route("/databases")
def databases():
    
    databases = []
    total_indexes = 0
    total_size = 0
    total_index_size = 0
    for database in g.mongo.database_names():
        this_db = pymongo.database.Database(g.mongo, database)
        for coll in this_db.collection_names():
            try:
                idx_info = this_db.command("collstats", coll)
            except pymongo.OperationalError, e:
                print e
                
            total_indexes += idx_info.get("nindexes")
            total_size += idx_info.get("storageSize")
            total_index_size += idx_info.get("totalIndexSize")
        
        db = dict(
            name=database, 
            size=total_size, 
            indexes=total_indexes, 
            collections=len(this_db.collection_names()),
            index_size=total_index_size,
        )
        databases.append(db)
    
    return render_template("index.html", databases=databases)
    

@app.before_request
def connect_mongo():
    g.mongo = pymongo.Connection("localhost", 27017)
        
        
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=27018, debug=True)