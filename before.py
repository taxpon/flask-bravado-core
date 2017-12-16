from typing import Dict
import attr
from flask import Flask, request, jsonify


app = Flask(__name__)


@attr.s
class Book:
    title: str = attr.ib()
    published_year: int = attr.ib()


Books: Dict[int, Book] = {
    1: Book('The Internet Galaxy', 2003),
    2: Book('Prison Notebooks', 2010)
}


@app.route('/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
def book(book_id: int):
    target = Books.get(book_id)
    if not target:
        return jsonify(error=404, text="No book with book_id: {}".format(book_id)), 404

    if request.method == 'GET':
        resp = attr.asdict(target)
        resp.update({'id': book_id})
        return jsonify(resp)

    elif request.method == 'PUT':
        req = request.json
        if not req:
            return jsonify(error=400, text="Bad request"), 400

        if 'id' not in req or \
           'title' not in req or \
           'published_year' not in req:
            return jsonify(error=400, text="Bad request"), 400

        if not isinstance(req['title'], str):
            return jsonify(error=400, text="Bad request"), 400

        if not isinstance(req['published_year'], int):
            return jsonify(error=400, text="Bad request"), 400

        if book_id != req['id']:
            return jsonify(error=400, text="Bad request"), 400

        target.title = req['title']
        target.published_year = req['published_year']

        resp = attr.asdict(target)
        resp.update({'id': book_id})
        return jsonify(resp)

    elif request.method == 'DELETE':
        del Books[book_id]
        return '', 204
    return


if __name__ == '__main__':
    app.run(debug=True)
