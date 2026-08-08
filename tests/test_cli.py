import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "taiwan-transit"
sys.path.insert(0, str(SKILL_ROOT))

from scripts import cli


class FakeResponse:
    def __init__(self, body, status=200, headers=None):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        return self.responses.pop(0)

    @property
    def request_methods(self):
        return [request.get_method() for request in self.requests]

    @property
    def posted_forms(self):
        forms = []
        for request in self.requests:
            data = request.data
            if data is not None:
                forms.append(parse_qs(data.decode("utf-8")))
        return forms

    @property
    def urls(self):
        return [request.full_url for request in self.requests]


class FailingOpener:
    def __call__(self, request):
        raise URLError("certificate verify failed")


def write_tra_cache(directory, stations):
    path = Path(directory) / "tra_stations.json"
    path.write_text(json.dumps(stations, ensure_ascii=False), encoding="utf-8")
    return path


class TaiwanTransitCliTests(unittest.TestCase):
    def test_default_tra_cache_lives_under_scripts_data(self):
        expected = SKILL_ROOT / "scripts" / "data" / "tra_stations.json"

        self.assertEqual(cli.load_default_cache_path(), expected)
        self.assertTrue(expected.exists())

    def test_update_writes_tra_station_cache_from_government_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "tra_stations.json"
            csv_body = (
                "\ufeffstationCode,stationName,stationEName,name,ename\n"
                "1194,六家,Liujia,六家,Liujia\n"
                "1170,新豐,Xinfeng,新豐,Xinfeng\n"
                "1000,臺北,Taipei,臺北,Taipei\n"
            )
            opener = FakeOpener([FakeResponse(csv_body)])
            out = io.StringIO()

            exit_code = cli.main(
                ["update", "--cache", str(cache_path), "--json"],
                opener=opener,
                stdout=out,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(opener.request_methods, ["GET"])
            self.assertEqual(opener.urls, [cli.TRA_STATION_CSV_URL])
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(
                cached,
                [
                    {"code": "1194", "name": "六家", "aliases": []},
                    {"code": "1170", "name": "新豐", "aliases": []},
                    {"code": "1000", "name": "臺北", "aliases": ["台北"]},
                ],
            )
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["updated"], 3)

    def test_update_reports_network_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "tra_stations.json"
            err = io.StringIO()

            exit_code = cli.main(
                ["update", "--cache", str(cache_path)],
                opener=FailingOpener(),
                stderr=err,
            )

            self.assertEqual(exit_code, 2)
            self.assertIn("官方站點請求失敗", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())

    def test_cli_does_not_expose_insecure_option(self):
        parser = cli._build_parser()
        commands = [
            ["update", "--insecure"],
            [
                "hsr",
                "--from",
                "台北",
                "--to",
                "台中",
                "--date",
                "2026/08/08",
                "--time",
                "08:00",
                "--insecure",
            ],
            [
                "tra",
                "--from",
                "六家",
                "--to",
                "新豐",
                "--date",
                "2026/08/08",
                "--insecure",
            ],
        ]

        for command in commands:
            with self.subTest(command=command), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    parser.parse_args(command)
                self.assertEqual(raised.exception.code, 2)

    def test_tra_query_fails_from_cache_before_network_when_station_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = write_tra_cache(
                tmpdir,
                [{"code": "1194", "name": "六家", "aliases": []}],
            )
            opener = FakeOpener(
                [
                    FakeResponse(
                        '<input name="_csrf" value="token">'
                        '<button class="btn tipStation" title="1170-新豐">新豐</button>'
                    )
                ]
            )
            err = io.StringIO()

            exit_code = cli.main(
                [
                    "tra",
                    "--from",
                    "六家",
                    "--to",
                    "新豐",
                    "--date",
                    "2026/08/08",
                    "--cache",
                    str(cache_path),
                    "--json",
                ],
                opener=opener,
                stderr=err,
            )

            self.assertEqual(exit_code, 2)
            self.assertEqual(opener.requests, [])
            self.assertIn("車站快取找不到：新豐", err.getvalue())

    def test_tra_query_uses_cached_station_values_in_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = write_tra_cache(
                tmpdir,
                [
                    {"code": "1194", "name": "六家", "aliases": []},
                    {"code": "1170", "name": "新豐", "aliases": []},
                ],
            )
            opener = FakeOpener(
                [
                    FakeResponse('<input value="csrf-token" name="_csrf">'),
                    FakeResponse(
                        """
                        <table class="itinerary-controls">
                          <caption>建議搭乘車次</caption>
                          <tr class="trip-column">
                            <td class="train-number">1701</td>
                            <td class="train-type">區間</td>
                            <td class="departure">06:23</td>
                            <td class="arrival">07:05</td>
                            <td class="duration">00:42</td>
                          </tr>
                        </table>
                        """
                    ),
                ]
            )
            out = io.StringIO()

            exit_code = cli.main(
                [
                    "tra",
                    "--from",
                    "六家",
                    "--to",
                    "新豐",
                    "--date",
                    "2026/08/08",
                    "--start-time",
                    "06:00",
                    "--end-time",
                    "09:00",
                    "--cache",
                    str(cache_path),
                    "--json",
                ],
                opener=opener,
                stdout=out,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(opener.request_methods, ["GET", "POST"])
            form = opener.posted_forms[0]
            self.assertEqual(form["startStation"], ["1194-六家"])
            self.assertEqual(form["endStation"], ["1170-新豐"])
            self.assertEqual(form["transfer"], ["ONE"])
            self.assertEqual(form["rideDate"], ["2026/08/08"])
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["results"][0]["train_number"], "1701")

    def test_hsr_filters_by_requested_date_and_time(self):
        response = {
            "success": True,
            "data": {
                "DepartureTable": {
                    "TrainItem": [
                        {
                            "TrainNumber": "0999",
                            "DepartureDate": "08/07",
                            "DepartureTime": "23:55",
                            "DestinationTime": "00:50",
                            "Duration": "00:55",
                        },
                        {
                            "TrainNumber": "0601",
                            "DepartureDate": "08/08",
                            "DepartureTime": "07:50",
                            "DestinationTime": "08:40",
                            "Duration": "00:50",
                        },
                        {
                            "TrainNumber": "0801",
                            "DepartureDate": "08/08",
                            "DepartureTime": "08:10",
                            "DestinationTime": "09:00",
                            "Duration": "00:50",
                        },
                    ]
                }
            },
        }
        opener = FakeOpener([FakeResponse(json.dumps(response))])
        out = io.StringIO()

        exit_code = cli.main(
            [
                "hsr",
                "--from",
                "台北",
                "--to",
                "台中",
                "--date",
                "2026/08/08",
                "--time",
                "08:00",
                "--json",
            ],
            opener=opener,
            stdout=out,
        )

        self.assertEqual(exit_code, 0)
        form = opener.posted_forms[0]
        self.assertEqual(form["StartStation"], ["TaiPei"])
        self.assertEqual(form["EndStation"], ["TaiZhong"])
        self.assertEqual(form["OutWardSearchDate"], ["2026/08/08"])
        payload = json.loads(out.getvalue())
        self.assertEqual([item["train_number"] for item in payload["results"]], ["0801"])


if __name__ == "__main__":
    unittest.main()
