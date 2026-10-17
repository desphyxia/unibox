"""Underwater backdrop for the 3D sea-horse renders: the same scene the 2D rig draws, without any creature.
Usage: python backdrop.py OUT.svg"""
import sys
import seahorse as R

D = R.Doc(R.pastel, "bk")
D.base((150, 660))
o = R.draw_scene(D, (400, 330))
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -30 {R.W} {R.H + 30}"><defs>' + "".join(D.defs) + "</defs>" + "".join(o) + "</svg>")
open(sys.argv[1], "w", encoding="utf-8").write(svg)
