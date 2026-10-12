import csv
import json
import unittest
from datetime import date

import main


class ReminderTests(unittest.TestCase):
    def test_stages(self):
        rows = list(csv.DictReader(open("sample_invoices.csv")))
        outbox, esc, skipped = main.run(rows, json.load(open("stages.json")), date(2026, 10, 9))
        stages = {m["invoice"]: m["stage"] for msgs in outbox.values() for m in msgs}
        self.assertEqual(stages["INV-201"], "due soon")
        self.assertEqual(stages["INV-188"], "friendly")
        self.assertEqual(stages["INV-170"], "firm")
        self.assertEqual(stages["INV-150"], "final")
        self.assertEqual(stages["INV-120"], "escalate")
        self.assertEqual({s[0] for s in skipped}, {"INV-160", "INV-165", "INV-210"})
        self.assertEqual(len(esc), 2)


if __name__ == "__main__":
    unittest.main()
