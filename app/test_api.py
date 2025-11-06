from flask import Flask
from flask_restful import Api, Resource

class Hello(Resource):
    def get(self):
        return {"msg": "hello"}

def create_app():
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(Hello, "/api/scripts")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
