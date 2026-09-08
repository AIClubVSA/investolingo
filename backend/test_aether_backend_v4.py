import json
from pathlib import Path
import unittest
from aether_backend_v4 import Backend, advance, new_state, execute, portfolio_view

class BackendTests(unittest.TestCase):
  def test_deterministic_advance(self):
    a, b = new_state(), new_state()
    advance(a, 5); advance(b, 5)
    self.assertEqual(a["prices"], b["prices"])
    self.assertEqual(a["sim_day"], 5)

  def test_portfolio_buy_sell_and_fee(self):
    s = new_state(); start = s["portfolio"]["cash"]
    execute(s, "buy", "IRON", 2)
    self.assertEqual(s["portfolio"]["holdings"]["IRON"], 2)
    self.assertLess(s["portfolio"]["cash"], start)
    execute(s, "sell", "IRON", 1)
    self.assertEqual(s["portfolio"]["holdings"]["IRON"], 1)
    self.assertGreater(portfolio_view(s)["positions"][0]["value"], 0)

  def test_progression_unlocks(self):
    s = new_state(); execute(s, "buy", "IRON", 1); execute(s, "buy", "EMBR", 1); execute(s, "buy", "FRGE", 1)
    advance(s, 30)
    self.assertIn("first_trade", s["achievements"])
    self.assertIn("diversified", s["achievements"])
    self.assertIn("survivor", s["achievements"])

  def test_state_persists(self):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "state.json"; b = Backend(p); advance(b.state, 1); b.save()
      self.assertEqual(json.loads(p.read_text())["sim_day"], 1)

  def test_short_selling_rejected(self):
    with self.assertRaises(ValueError): execute(new_state(), "sell", "IRON", 1)

if __name__ == "__main__":
  unittest.main()
