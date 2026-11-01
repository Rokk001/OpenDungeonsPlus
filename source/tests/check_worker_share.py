"""Check the worker allocation rules replacing the previous share gates.

Use --static-only during the plan; the default runs the C++ allocation probe in FINAL.
"""
import check_worker_allocation  # Runs the same ten acceptance cases and R3/R5 cases.
