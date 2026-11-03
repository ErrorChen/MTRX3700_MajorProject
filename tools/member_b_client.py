"""Importable Member B client using the same real BCTL transactions as echo7.

Example: from member_b_client import MemberBClient
         reply = MemberBClient().locate("function", 1)

No classifier, ROM answer, slot-to-ID mapping or raw debug offset is exposed.
Every call retains the ordinary CLI JSON/log evidence in build/member_b.
"""
import argparse
from datetime import datetime, timezone
import json
import echo7


class MemberBClientError(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(result.get("reason", "Member B transaction failed"))


class MemberBClient:
    def __init__(self, *, quartusBin=None, cable=None, device=None, timeout=30):
        if type(timeout) is not int or timeout <= 0:
            raise ValueError("timeout must be a positive integer number of seconds")
        self.options = dict(quartus_bin=quartusBin, modelsim_bin=None,
                            cable=cable, device=device, timeout=timeout)

    def _execute(self, command, **options):
        runner = echo7.Runner(argparse.Namespace(command=command, **self.options, **options))
        try:
            runner.execute()
            runner.result.update(status="PASS", exitCode=0)
        except Exception as exc:
            runner.result.update(status="BLOCKED" if isinstance(exc, echo7.Blocked) else "FAIL",
                                 exitCode=2 if isinstance(exc, echo7.Blocked) else 1, reason=str(exc))
        runner.result["finishedUtc"] = datetime.now(timezone.utc).isoformat()
        (runner.out / "result.json").write_text(json.dumps(runner.result, indent=2) + "\n", encoding="utf-8")
        if runner.result["exitCode"]:
            raise MemberBClientError(runner.result)
        return runner.result

    def markers(self):
        """Return every FPGA-recognised position, including duplicate IDs and BJ."""
        return self._execute("markers", drain=False)

    def drain(self):
        """Recover an abandoned query without selecting or querying another ID."""
        return self._execute("markers", drain=True)

    def locate(self, markerType, digit=None):
        from query_transport import markerSelector
        markerSelector(markerType, digit)
        return self._execute("locate", type=markerType, digit=digit)

    def track(self, markerType, digit=None):
        from query_transport import markerSelector
        markerSelector(markerType, digit)
        return self._execute("track", type=markerType, digit=digit)

    def selectBay(self, bay):
        return self.track("bay", bay)

    def clear(self):
        return self._execute("clear")

    def status(self):
        """Read current board time/config/readiness before using cached results."""
        return self._execute("status")
