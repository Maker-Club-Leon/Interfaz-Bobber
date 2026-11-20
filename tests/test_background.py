import unittest

from mascota.background import gradient_pixels, parse_color


class BackgroundTests(unittest.TestCase):
    def test_parse_color(self):
        self.assertEqual(parse_color("#ff0000"), (1.0, 0.0, 0.0))
        self.assertEqual(parse_color([0, 0.5, 1]), (0.0, 0.5, 1.0))
        with self.assertRaises(ValueError):
            parse_color("rojo")

    def test_gradient_goes_from_top_to_bottom(self):
        px = gradient_pixels((1, 1, 1), (0, 0, 0), (0, 0, 0), 0.0, size=(64, 36))
        self.assertEqual(px.shape, (36, 64, 3))
        self.assertGreater(px[0, 32].mean(), 200)    # arriba: claro
        self.assertLess(px[-1, 32].mean(), 30)       # abajo: oscuro

    def test_glow_lights_the_center(self):
        plain = gradient_pixels((0, 0, 0), (0, 0, 0), (1, 1, 1), 0.0, size=(64, 36))
        glow = gradient_pixels((0, 0, 0), (0, 0, 0), (1, 1, 1), 0.5, size=(64, 36))
        self.assertGreater(glow[15, 32].mean(), plain[15, 32].mean() + 50)


if __name__ == "__main__":
    unittest.main()
