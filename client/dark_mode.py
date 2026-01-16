import wx
import ctypes
import winreg
from ctypes import wintypes

# Try to check for wx.combo.ComboCtrl dynamically
# Some installations might not have it exposed directly or it might be missing
ComboCtrlType = None
try:
    import wx.combo
    ComboCtrlType = wx.combo.ComboCtrl
except ImportError:
    pass

# Constants for DWM and UXTHEME
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
# Undocumented ordinal for SetPreferredAppMode in uxtheme.dll
# 135 is supported in Windows 10 1903+
ORD_SetPreferredAppMode = 135

def is_system_dark():
    """Check registry for Windows Dark Mode setting."""
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False

def _enable_native_dark_mode():
    """Attempt to enable dark mode for controls via uxtheme.dll."""
    try:
        # Load uxtheme.dll
        uxtheme = ctypes.windll.uxtheme
        # Attempt to find SetPreferredAppMode by ordinal 135
        if hasattr(uxtheme, "SetPreferredAppMode"):
             # Enum: Default=0, AllowDark=1, ForceDark=2, ForceLight=3, Max=4
            uxtheme.SetPreferredAppMode(2) # Force Dark
        else:
            # Try getting by ordinal
            try:
                SetPreferredAppMode = uxtheme[135]
                SetPreferredAppMode(2)
            except Exception:
                pass
    except Exception:
        pass

def sync_window(window):
    """
    Apply dark mode attributes to the window and its children based on system settings.
    Should be called in __init__ and on EVT_SYS_COLOUR_CHANGED.
    """
    if wx.Platform != '__WXMSW__':
        return

    is_dark = is_system_dark()
    hwnd = window.GetHandle()
    
    # 1. Apply DWM Window Attribute (Title bar and border)
    # 1 = True (Dark), 0 = False (Light)
    enable = ctypes.c_int(1 if is_dark else 0)
    
    # Try the modern attribute first (Win 10 2004+)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 
            DWMWA_USE_IMMERSIVE_DARK_MODE, 
            ctypes.byref(enable), 
            ctypes.sizeof(enable)
        )
    except Exception:
        # Try older attribute (Win 10 1903-1909)
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 
                ctypes.byref(enable), 
                ctypes.sizeof(enable)
            )
        except Exception:
            pass

    # 2. Update Colors for standard widgets
    # While DWM handles the frame, wxWidgets controls often default to system 
    # colors that don't auto-switch without a manifest. We manually palette swap 
    # standard controls to ensure consistency.
    
    if is_dark:
        bg_col = wx.Colour(32, 32, 32)
        fg_col = wx.Colour(240, 240, 240)
        
        # Slightly lighter for input fields to distinguish them
        input_bg_col = wx.Colour(45, 45, 45)
        
        window.SetBackgroundColour(bg_col)
        window.SetForegroundColour(fg_col)
    else:
        # Reset to null to use system default
        window.SetBackgroundColour(wx.NullColour)
        window.SetForegroundColour(wx.NullColour)
        bg_col = wx.NullColour
        fg_col = wx.NullColour
        input_bg_col = wx.NullColour

    # Define control categories dynamically
    input_controls_list = [wx.TextCtrl, wx.ListBox, wx.TreeCtrl, wx.ComboBox]
    if ComboCtrlType:
        input_controls_list.append(ComboCtrlType)
    input_controls = tuple(input_controls_list)
    
    standard_controls = (
        wx.Panel, 
        wx.Button, 
        wx.CheckBox, 
        wx.RadioButton, 
        wx.StaticText, 
        wx.Notebook
    )

    def apply_recursive(w):
        # Don't override custom controls that might have their own paint handlers 
        # unless necessary, but do handle standard container/input types.
        
        if is_dark:
            if isinstance(w, input_controls):
                w.SetBackgroundColour(input_bg_col)
                w.SetForegroundColour(fg_col)
            elif isinstance(w, standard_controls):
                w.SetBackgroundColour(bg_col)
                w.SetForegroundColour(fg_col)
            else:
                w.SetBackgroundColour(bg_col)
                w.SetForegroundColour(fg_col)
        else:
            w.SetBackgroundColour(wx.NullColour)
            w.SetForegroundColour(wx.NullColour)
            
        w.Refresh()
        for child in w.GetChildren():
            apply_recursive(child)

    apply_recursive(window)
    window.Refresh()
    window.Update()

# Attempt to enable global preference on import
if wx.Platform == '__WXMSW__':
    _enable_native_dark_mode()