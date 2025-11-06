# Task 2.2: Integrate the "Discontinued Check" Feature - Completion

**Status:** Completed

**Summary:** The `gui.py` file was updated to implement the "Check Discontinued" feature. The button is now connected to a slot that opens a file dialog and uses a generic `_run_worker` method to execute the `run_discontinued_check` function in a background thread. The worker's signals are connected to the UI to provide feedback, and all buttons are disabled during the operation.
