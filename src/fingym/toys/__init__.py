"""Toy worlds.

Minimal environments with known ground truth, used to validate the evaluator
and agent pipeline before applying them to finance, where ground truth is
debatable.

Per DESIGN.md "Calibrate the Evaluator in a Toy First" (Intuition 7):
a scoring rule that fails in the coin world will fail silently in the
real world.
"""
