"""End-to-end HTTP checks against an ephemeral local server."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import server

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.httpd.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join()

    def post(self, value):
        req = Request(self.base + '/api/action', data=json.dumps(value).encode(),
                      headers={'Content-Type':'application/json'}, method='POST')
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    def test_presentation_flow(self):
        with urlopen(self.base + '/', timeout=5) as response:
            self.assertIn('巡检地图', response.read().decode())
        self.post({'action':'reset'})
        self.assertEqual(self.post({'action':'move', 'direction':'right'})['x'], 2)
        for target in range(len(server.POINTS)):
            for _ in range(100):
                result = self.post({'action':'step', 'target':target})
                if (result['x'], result['y']) == server.POINTS[target]: break
            else: self.fail('巡检点未到达')
        self.assertEqual(result['path'], [])
        result = self.post({'action':'reset'})
        self.assertEqual((result['x'], result['y'], result['steps']), (1, 1, 0))

    def test_bad_request_returns_400(self):
        with self.assertRaises(HTTPError) as error:
            self.post({'action':'move', 'direction':[]})
        self.assertEqual(error.exception.code, 400)
        error.exception.close()

if __name__ == '__main__': unittest.main()
