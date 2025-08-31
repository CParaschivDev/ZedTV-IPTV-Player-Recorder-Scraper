# --- PySimpleGUI v4/v5 compatibility shim ---
try:
    import PySimpleGUI as sg
except ImportError:
    print("ERROR: PySimpleGUI not installed. Please install it with: pip install PySimpleGUI")
    raise

# If neither InputText nor Input exists, define a minimal InputText using Multiline as fallback.
if not hasattr(sg, "InputText") and not hasattr(sg, "Input"):
    # Fallback factory: behaves like single-line input using Multiline
    def _InputText(*args, **kwargs):
        kwargs.setdefault("size", (20,1))
        kwargs.setdefault("no_scrollbar", True)
        kwargs.setdefault("enter_submits", True)
        kwargs.setdefault("expand_x", True)
        return sg.Multiline(*args, **kwargs)
    sg.InputText = _InputText
elif not hasattr(sg, "InputText") and hasattr(sg, "Input"):
    sg.InputText = sg.Input  # v5 rename
elif not hasattr(sg, "Input") and hasattr(sg, "InputText"):
    sg.Input = sg.InputText  # old name only

if not hasattr(sg, "SimpleButton"):
    sg.SimpleButton = sg.Button
if not hasattr(sg, "Submit"):
    def _Submit(*args, **kwargs): return sg.Button("Submit", *args, **kwargs)
    sg.Submit = _Submit
if not hasattr(sg, "OK"):
    def _OK(*a, **k): return sg.Button("OK", *a, **k)
    sg.OK = _OK
if not hasattr(sg, "Cancel"):
    def _Cancel(*a, **k): return sg.Button("Cancel", *a, **k)
    sg.Cancel = _Cancel
# --- end shim ---
