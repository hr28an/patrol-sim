import unittest
import server

class PatrolTests(unittest.TestCase):
    def setUp(self): server.action({'action':'reset'})
    def test_blocked_and_bounds(self):
        server.state.update(x=3,y=1)
        self.assertEqual(server.action({'action':'move','direction':'right'})['x'],3)
        server.state.update(x=0,y=0)
        self.assertEqual(server.action({'action':'move','direction':'left'})['x'],0)
    def test_routes_reach_all_points_without_crossing_walls(self):
        start=(1,1)
        for goal in server.POINTS:
            path=server.route(start,goal)
            self.assertTrue(path); self.assertEqual(path[-1],goal)
            for a,b in zip([start]+path,path):
                self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),1)
                self.assertNotIn(b,server.WALLS)
            start=goal
    def test_simulated_sensor_and_battery(self):
        s = server.snapshot()
        self.assertEqual(s['battery'], 100)
        self.assertEqual(s['sensor']['up'], 1)
        server.action({'action':'move','direction':'right'})
        self.assertEqual(server.snapshot()['battery'], 99)
    def test_auto_and_invalid(self):
        for _ in range(100): server.action({'action':'step','target':0})
        self.assertEqual((server.state['x'],server.state['y']),server.POINTS[0])
        with self.assertRaises(ValueError): server.action({'action':'step','target':-1})
if __name__ == '__main__': unittest.main()
