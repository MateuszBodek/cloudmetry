import unittest

import pandas as pd

from dashboard.app import _format, _route_figure


class RouteFigureTests(unittest.TestCase):
    def test_map_fits_sampled_route_and_uses_dark_basemap(self) -> None:
        point_count = 22_113
        route = pd.DataFrame(
            {
                "elapsed_drive_time_s": range(point_count),
                "latitude": [51 + index / 60_000 for index in range(point_count)],
                "longitude": [17 + index / 30_000 for index in range(point_count)],
                "effective_speed_kmh": range(point_count),
                "combined_g_force": [index / 1000 for index in range(point_count)],
            }
        )

        figure = _route_figure(route, title="Test", height=430)

        self.assertIsNotNone(figure)
        if figure is None:
            self.fail("Expected a route figure when GPS coordinates are available.")
        self.assertEqual(figure.layout.map.style, "carto-darkmatter")
        self.assertEqual(figure.layout.map.fitbounds, "locations")
        self.assertIsNone(figure.layout.map.center.lat)
        self.assertIsNone(figure.layout.map.center.lon)
        self.assertIsNone(figure.layout.map.zoom)
        line_latitudes = list(figure.data[0].lat)
        self.assertEqual(
            len(line_latitudes), len(range(0, point_count, point_count // 2500))
        )
        self.assertEqual(len(figure.data[1].lat), len(line_latitudes))

    def test_map_can_color_route_points_by_combined_g_force(self) -> None:
        route = pd.DataFrame(
            {
                "latitude": [51.0, 51.1],
                "longitude": [17.0, 17.1],
                "effective_speed_kmh": [20.0, 40.0],
                "combined_g_force": [0.12, 0.35],
            }
        )

        figure = _route_figure(
            route,
            title="Test",
            height=430,
            color_by="combined_g_force",
        )

        self.assertIsNotNone(figure)
        if figure is None:
            self.fail("Expected a route figure when GPS coordinates are available.")
        self.assertEqual(list(figure.data[1].marker.color), [0.12, 0.35])
        self.assertEqual(figure.data[1].marker.colorbar.title.text, "G")
        self.assertIn("Łączne G:", figure.data[1].hovertemplate)

    def test_unrounded_fuel_format_preserves_source_precision(self) -> None:
        self.assertEqual(
            _format(0.9973333333333333, "L", digits=None), "0.9973333333333333 L"
        )
