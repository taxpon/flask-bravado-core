from typing import Dict, Callable
from functools import wraps
import attr
from flask import Flask, request, jsonify

import yaml
from jsonschema.exceptions import ValidationError
from bravado_core.spec import Spec
from bravado_core.request import IncomingRequest
from bravado_core.request import unmarshal_request


class OpenAPIError(Exception):
    pass


class OpenAPI:
    def __init__(self, doc_path: str, config: dict = None) -> None:
        with open(doc_path, "r") as fp:
            self._raw_spec: dict = yaml.load(fp)
        self.spec: Spec = Spec.from_dict(self._raw_spec, config=config)

    def unmarshal_request(self) -> dict:
        b_req = BravadoRequest(self)
        operation = self.spec.get_op_for_request(request.method.lower(), b_req.endpoint())
        if not operation:
            raise OpenAPIError('Failed to find proper operation method = {}, endpoint = {}'.format(
                request.method.lower(), b_req.endpoint()
            ))
        return unmarshal_request(b_req, operation)


class BravadoRequest(IncomingRequest):
    def __init__(self, openapi: OpenAPI) -> None:
        self.openapi: OpenAPI = openapi

    def endpoint(self) -> str:
        import re
        flask_path: str = str(request.url_rule)
        spec_path_pattern = re.sub(r'<(?:[a-z]+:)?(\w+)>', r'{\1}', flask_path)

        if self.openapi.spec._request_to_op_map is None:
            self.openapi.spec.get_op_for_request("get", "")

        for method, url in self.openapi.spec._request_to_op_map.keys():
            result = re.match(spec_path_pattern, url)
            if result is not None \
                    and result.group(0) == url \
                    and request.method.lower() == method:
                return url

    @property
    def path(self) -> dict:
        return request.view_args

    @property
    def query(self) -> dict:
        return dict(request.args)

    @property
    def form(self) -> dict:
        return request.form

    @property
    def headers(self) -> dict:
        return request.headers

    def json(self) -> dict:
        return request.json


app = Flask(__name__)


@attr.s
class Book:
    title: str = attr.ib()
    published_year: int = attr.ib()


Books: Dict[int, Book] = {
    1: Book('The Internet Galaxy', 2003),
    2: Book('Prison Notebooks', 2010)
}


@app.errorhandler(ValidationError)
def validation_error(e: ValidationError):
    app.logger.exception(e)
    return jsonify(error=400, text="Bad request"), 400


def extract_params(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        openapi = OpenAPI('openapi.yaml')
        client_req = openapi.unmarshal_request()
        kwargs.update(client_req)
        return func(*args, **kwargs)

    return wrapped


@app.route('/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
@extract_params
def book(book_id: int, params: dict = None):
    target = Books.get(book_id)
    if not target:
        return jsonify(error=404, text="No book with book_id: {}".format(book_id)), 404

    if request.method == 'GET':
        resp = attr.asdict(target)
        resp.update({'id': book_id})
        return jsonify(resp)

    elif request.method == 'PUT':
        if book_id != params['id']:
            return jsonify(error=400, text="Bad request"), 400

        target.title = params['title']
        target.published_year = params['published_year']

        resp = attr.asdict(target)
        resp.update({'id': book_id})
        return jsonify(resp)

    elif request.method == 'DELETE':
        del Books[book_id]
        return '', 204
    return


if __name__ == '__main__':
    app.run(debug=True)
