"""
app.py  -  Flask backend (DSA Graph Edition)
Run:
    python import_books.py
    python app.py
"""

from flask import Flask, render_template, request
from recommender import RecommendationEngine

app = Flask(__name__)
DB  = "library.db"

# Initialize the DSA Engine (Builds the Graph and Data Maps in memory)
engine = RecommendationEngine(DB)

@app.context_processor
def _globals():
    return dict(
        query=request.args.get("q", "") or "",
        selected_genre=request.args.get("genre", "") or "",
        selected_author=request.args.get("author", "") or "",
        selected_language=request.args.get("language", "") or "",
        selected_purpose=request.args.get("purpose", "") or "",
        selected_length=request.args.get("length", "") or "",
        selected_mood=request.args.get("mood", "") or ""
    )

@app.route("/")
def index():
    q               = request.args.get("q", "").strip()
    sort            = request.args.get("sort", "rating")
    selected_genre  = request.args.get("genre", "").strip()
    selected_author = request.args.get("author", "").strip()

    books = engine.search(q) if q else engine.all_books()

    if selected_genre:
        books = [b for b in books if b.genre == selected_genre]
    if selected_author:
        books = [b for b in books if b.author == selected_author]

    key = {
        "rating": lambda b: -b.rating,
        "year":   lambda b: -b.year,
        "title":  lambda b: b.title.lower()
    }.get(sort, lambda b: -b.rating)
    
    books = sorted(books, key=key)
    
    return render_template(
        "index.html", 
        books=books, 
        q=q, 
        sort=sort,
        selected_genre=selected_genre,
        selected_author=selected_author,
        genres=engine.genres(),
        authors=engine.authors(),
        languages=engine.languages(),
        purposes=engine.purposes(),
        lengths=engine.lengths(),
        moods=engine.moods()
    )

@app.route("/recommend")
def recommend():
    q                = request.args.get("q", "").strip()
    sort             = request.args.get("sort", "rating")
    selected_genre   = request.args.get("genre", "").strip()
    selected_language = request.args.get("language", "").strip()
    selected_purpose = request.args.get("purpose", "").strip()
    selected_length  = request.args.get("length", "").strip()
    selected_mood    = request.args.get("mood", "").strip()

    books = engine.filter_books(
        q=q,
        genre=selected_genre,
        language=selected_language,
        purpose=selected_purpose,
        length=selected_length,
        mood=selected_mood,
    )

    key = {
        "rating": lambda b: -b.rating,
        "year":   lambda b: -b.year,
        "title":  lambda b: b.title.lower()
    }.get(sort, lambda b: -b.rating)

    books = sorted(books, key=key)

    return render_template(
        "recommend.html",
        books=books
    )

@app.route("/top-rated")
def top_rated():
    return render_template(
        "top_rated.html",
        top=engine.top_rated(20)
    )

@app.route("/book/<int:bid>")
def detail(bid):
    # Fetch the specific book from the O(1) dictionary map
    book = engine.get_book(bid)
    if not book: 
        return "Book Not Found", 404
    
    # Run the Graph BFS + Min-Heap logic to get Top K recommendations
    similar_books = engine.similar(bid)
    
    return render_template(
        "detail.html", 
        book=book, 
        similar=similar_books
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
