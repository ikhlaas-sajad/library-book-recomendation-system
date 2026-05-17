
"""
recommender.py  -  Pure DSA Engine (Graph BFS + Min-Heap)

DSA Architecture:
  1. Adjacency List Graph: Connects books by shared Author or Genre.
  2. Breadth-First Search (BFS): Finds shortest path (degrees of separation) between books.
  3. Min-Heap (heapq): Maintains the Top-K closest books in O(V+E + N log K) time.
"""

import heapq
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class Book:
    id: int
    title: str
    author: str
    genre: str
    year: int
    rating: float
    pages: int
    description: str
    image_url: str = ""
    language: str = "English"
    purpose: str = ""
    length: str = ""
    moods: str = ""

class RecommendationEngine:
    def __init__(self, db_path: str):
        self._books: List[Book] = []
        self._id_map: Dict[int, Book] = {}
        self.graph: Dict[int, List[int]] = defaultdict(list)
        self._load_data(db_path)

    def _load_data(self, db_path: str):
        # Open DB, fetch all rows, and close immediately.
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM books").fetchall()
        conn.close()

        # Load into memory structures
        book_fields = set(Book.__dataclass_fields__.keys())
        for r in rows:
            data = {k: r[k] for k in r.keys() if k in book_fields}
            b = Book(**data)
            if not b.length:
                b.length = self.page_length_category(b.pages)
            self._books.append(b)
            self._id_map[b.id] = b

        self._build_graph()

    def _build_graph(self):
        """
        Builds an undirected graph (Adjacency List).
        Includes edges for shared Genre, Author, Language, Purpose, Length, and Mood.
        """
        attr_maps = defaultdict(lambda: defaultdict(list))

        for b in self._books:
            attr_maps['genre'][b.genre].append(b.id)
            attr_maps['author'][b.author].append(b.id)
            attr_maps['language'][b.language].append(b.id)
            attr_maps['purpose'][b.purpose].append(b.id)
            attr_maps['length'][b.length].append(b.id)
            for mood in self.mood_list(b):
                attr_maps['mood'][mood].append(b.id)

        for b in self._books:
            neighbors = set()
            for attr in ('genre', 'author', 'language', 'purpose', 'length'):
                for neighbor_id in attr_maps[attr].get(getattr(b, attr), []):
                    if neighbor_id != b.id:
                        neighbors.add(neighbor_id)
            for mood in self.mood_list(b):
                for neighbor_id in attr_maps['mood'][mood]:
                    if neighbor_id != b.id:
                        neighbors.add(neighbor_id)

            self.graph[b.id] = list(neighbors)

    def all_books(self) -> List[Book]:
        return self._books

    def genres(self) -> List[str]:
        return sorted({b.genre for b in self._books})

    def authors(self) -> List[str]:
        return sorted({b.author for b in self._books})

    def languages(self) -> List[str]:
        return sorted({b.language for b in self._books if b.language})

    def purposes(self) -> List[str]:
        fixed = {"Learning", "Entertainment", "Motivation", "Career growth"}
        return sorted(fixed.union({b.purpose for b in self._books if b.purpose}))

    def lengths(self) -> List[str]:
        return ["Short", "Medium", "Long"]

    def moods(self) -> List[str]:
        moods = set()
        for b in self._books:
            moods.update(self.mood_list(b))
        return sorted(moods)

    def mood_list(self, book: Book) -> List[str]:
        return [m.strip() for m in book.moods.split(",") if m.strip()]

    def page_length_category(self, pages: int) -> str:
        if pages <= 200:
            return "Short"
        if pages <= 400:
            return "Medium"
        return "Long"

    def filter_books(
        self,
        q: str = "",
        genre: str = "",
        author: str = "",
        language: str = "",
        purpose: str = "",
        length: str = "",
        mood: str = "",
    ) -> List[Book]:
        books = self.search(q) if q else list(self._books)

        if genre:
            books = [b for b in books if b.genre == genre]
        if author:
            books = [b for b in books if b.author == author]
        if language:
            books = [b for b in books if b.language == language]
        if purpose:
            books = [b for b in books if b.purpose == purpose]
        if length:
            books = [b for b in books if b.length == length]
        if mood:
            books = [b for b in books if mood in self.mood_list(b)]

        return books

    def get_book(self, book_id: int):
        """
        Returns a single book object by its ID in O(1) time.
        (This fixes the AttributeError from app.py)
        """
        return self._id_map.get(book_id)

    def top_rated(self, k=5) -> List[Book]:
        # Min-Heap for highest rated books
        heap = []
        for b in self._books:
            if len(heap) < k:
                heapq.heappush(heap, (b.rating, b.id))
            elif b.rating > heap[0][0]:
                heapq.heapreplace(heap, (b.rating, b.id))
        return [self._id_map[i] for _, i in sorted(heap, reverse=True)]

    def similar(self, book_id: int, k=4) -> List[Tuple[Book, float]]:
        """
        Uses Breadth-First Search (BFS) to find the shortest path to related books.
        Uses a Min-Heap bounded to size K to keep the closest matches.
        """
        if book_id not in self._id_map:
            return []

        # queue stores tuples of (current_book_id, distance_from_source)
        queue = deque([(book_id, 0)])
        visited = {book_id}
        heap = [] 

        while queue:
            curr_id, dist = queue.popleft()

            if curr_id != book_id:
                book = self._id_map[curr_id]
                
                # We want to keep the SMALLEST distance and HIGHEST rating.
                # In Python's Min-Heap, the root is the smallest item.
                # To make the heap discard the "worst" item (largest distance), 
                # we push negative distances. 
                # Tuple format: (-distance, rating, book.id)
                item = (-dist, book.rating, curr_id)

                if len(heap) < k:
                    heapq.heappush(heap, item)
                else:
                    # If the current book is "greater" (smaller distance or higher rating)
                    # than the worst book currently in the heap (heap[0]), we replace it.
                    if item > heap[0]:
                        heapq.heapreplace(heap, item)

            # Performance optimization: Don't explore paths longer than 3 degrees of separation
            if dist >= 3:
                continue

            # BFS Expansion: Add unvisited neighbors to the queue
            for neighbor_id in self.graph[curr_id]:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, dist + 1))

        # Format results for the frontend
        results = []
        while heap:
            neg_dist, rating, b_id = heapq.heappop(heap)
            
            # Convert the BFS distance back into a "Match Percentage" for the HTML template
            # Distance 1 -> 95%, Distance 2 -> 80%, etc.
            match_percentage = max(0.95 - (abs(neg_dist) - 1) * 0.15, 0.10)
            
            results.append((self._id_map[b_id], match_percentage))

        # Reverse so the best matches (popped last) are at the top of the list
        results.reverse()
        return results

 
    
    def search(self, query: str) -> List[Book]:
        """
        Basic O(N) linear search for the search bar functionality.
        Includes title, author, genre, language, purpose, and mood tags.
        """
        q = query.lower().strip()
        results = []

        for b in self._books:
            mood_matches = any(q in m.lower() for m in self.mood_list(b))
            if (
                q in b.title.lower() or
                q in b.author.lower() or
                q in b.genre.lower() or
                q in b.language.lower() or
                q in b.purpose.lower() or
                mood_matches
            ):
                results.append(b)

        return results