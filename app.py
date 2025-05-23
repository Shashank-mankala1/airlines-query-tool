from flask import Flask, render_template, request, send_file, session
import psycopg2
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def connect_db():
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    return conn


def get_table_and_column_info():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;""")
    
    tables = cur.fetchall()

    table_info = {}
    for table in tables:
        table_name = table[0]
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;""", (table_name,))
        columns = cur.fetchall()
        table_info[table_name] = columns

    cur.close()
    conn.close()
    return table_info


def run_user_query(user_query):
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute(user_query)
        if cur.description:
            columns = [desc[0] for desc in cur.description]
            results = cur.fetchall()
        else:
            columns = []
            results = []
        conn.commit()
    except Exception as e:
        columns = []
        results = [[str(e)]]
    cur.close()
    conn.close()
    return columns, results

@app.route("/", methods=["GET", "POST"])
def home():
    table_info = get_table_and_column_info()
    default_query = "SELECT * FROM flights LIMIT 5;"
    columns = []
    results = []

    if request.method == "POST":
        user_query = request.form["query"]
        columns, results = run_user_query(user_query)
        session['columns'] = columns
        session['results'] = results
        default_query = user_query

    return render_template("index.html", table_info=table_info, columns=columns, results=results, default_query=default_query)

@app.route("/download_csv")
def download_csv():
    columns = session.get("columns")
    results = session.get("results")

    if not columns or not results:
        return "No query result to export."

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows(results)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), 
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='query_result.csv')

if __name__ == "__main__":
    app.run(debug=True)
