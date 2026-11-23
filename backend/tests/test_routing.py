import httpx
import pytest

from app.routing import EstimateRouter, OsrmRouter, RoutingUnavailable
from app.routing.polyline import decode, encode
from app.schema import LatLng

A = LatLng(lat=14.2134403, lng=121.1667919)
B = LatLng(lat=14.2123167, lng=121.18708)


def test_polyline_round_trip():
    pts = [A, B, LatLng(lat=14.0, lng=121.0)]
    back = decode(encode(pts))
    assert [(round(p.lat, 6), round(p.lng, 6)) for p in back] == [(round(p.lat, 6), round(p.lng, 6)) for p in pts]


def test_estimate_is_longer_than_straight_line_and_adds_parking():
    d = EstimateRouter().drive(A, B)
    assert 2700 < d.distance_m < 3000  # 2.2 km straight line x 1.35
    assert d.duration_s > 120


def test_osrm_parses_route_and_caches():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url)
        assert req.url.params["geometries"] == "polyline6"
        route = {"distance": 3012.4, "duration": 480.2, "geometry": "abc"}
        return httpx.Response(200, json={"code": "Ok", "routes": [route]})

    r = OsrmRouter("https://osrm.test", httpx.Client(transport=httpx.MockTransport(handler)))
    d = r.drive(A, B)
    assert (d.distance_m, d.duration_s, d.geometry) == (3012, 480 + 120, "abc")
    r.drive(A, B)
    assert len(calls) == 1


@pytest.mark.parametrize("resp", [httpx.Response(503), httpx.Response(200, json={"code": "NoRoute", "routes": []})])
def test_osrm_failure_raises_unavailable(resp):
    r = OsrmRouter("https://osrm.test", httpx.Client(transport=httpx.MockTransport(lambda _: resp)))
    with pytest.raises(RoutingUnavailable):
        r.drive(A, B)
